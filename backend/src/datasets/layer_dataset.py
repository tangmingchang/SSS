"""图层数据集 - 从图层数据创建训练样本"""
import torch
from torch.utils.data import Dataset
from pathlib import Path
from typing import List, Dict
import cv2
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import math


class LayerDataset(Dataset):
    """图层数据集"""
    
    def __init__(
        self,
        characters_dir: str,
        img_size=(512, 768),
        num_variations_per_char: int = 10
    ):
        self.characters_dir = Path(characters_dir)
        self.img_size = img_size
        self.num_variations = num_variations_per_char
        
        from src.layers import LayerLoader, LayerComposer
        from src.pose import PoseDetector
        
        self.loader = LayerLoader()
        self.composer = LayerComposer(self.loader)
        self.detector = PoseDetector()
        
        # 加载所有角色
        self.samples = []
        for char_dir in sorted(self.characters_dir.iterdir()):
            if char_dir.is_dir():
                try:
                    layers = self.loader.load_character(str(char_dir))
                    # 为每个角色创建多个变体
                    for i in range(self.num_variations):
                        self.samples.append({
                            'character': char_dir.name,
                            'char_dir': str(char_dir),
                            'layers': layers,
                            'variant_id': i
                        })
                except Exception as e:
                    print(f"跳过 {char_dir.name}: {e}")
        
        print(f"创建了 {len(self.samples)} 个训练样本（{len(self.samples) // self.num_variations} 个角色）")
        
        # 图像变换
        self.transform = transforms.Compose([
            transforms.Resize(img_size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ])
        
        self.cond_transform = transforms.Compose([
            transforms.Resize(img_size),
            transforms.ToTensor(),
        ])
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # 加载图层
        if 'layers' not in sample or sample['layers'] is None:
            layers = self.loader.load_character(sample['char_dir'])
        else:
            layers = sample['layers']
        
        # 合成图像（添加随机变换）
        import random
        transformations = {}
        for layer_name in layers.keys():
            # 随机旋转和缩放
            transformations[layer_name] = {
                'translation': (256 + random.randint(-20, 20), 384 + random.randint(-20, 20)),
                'rotation': random.uniform(-10, 10),
                'scale': random.uniform(0.95, 1.05)
            }
        
        composed = self.composer.compose(layers, transformations)
        
        # 转换为RGB
        if composed.shape[2] == 4:
            alpha = composed[:, :, 3:4] / 255.0
            rgb = composed[:, :, :3]
            composed_rgb = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
        else:
            composed_rgb = composed[:, :, :3]
        
        ref_img = Image.fromarray(composed_rgb)
        
        # 检测关键点并生成姿态图
        keypoints = self.detector.detect(composed_rgb)
        
        # 应用变换
        ref_img_tensor = self.transform(ref_img)
        
        # 直接将关键点转换为51通道热图（不需要先转换为RGB图像）
        h, w = composed_rgb.shape[:2]
        pose_img_tensor = self._convert_to_pose_heatmap(keypoints, (h, w))
        
        # 调整尺寸以匹配ref_img
        if pose_img_tensor.shape[-2:] != ref_img_tensor.shape[-2:]:
            pose_img_tensor = torch.nn.functional.interpolate(
                pose_img_tensor.unsqueeze(0),
                size=ref_img_tensor.shape[-2:],
                mode='bilinear',
                align_corners=False
            ).squeeze(0)
        
        return {
            'img': ref_img_tensor,
            'tgt_pose': pose_img_tensor,
            'ref_img': ref_img_tensor,
            'clip_images': ref_img_tensor,
            'character': sample['character'],
            'source': 'layer'  # 添加source标识
        }
    
    def _keypoints_to_image(self, keypoints: Dict, img_shape: tuple) -> Image.Image:
        """将关键点转换为51通道热图（17个关键点 * 3通道：x, y, confidence）"""
        h, w = img_shape[:2]
        
        # COCO格式的17个关键点顺序
        coco_keypoints = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
        
        # 创建51通道热图（17个关键点 * 3）
        heatmap = np.zeros((h, w, 51), dtype=np.float32)
        
        for idx, kp_name in enumerate(coco_keypoints):
            if kp_name in keypoints:
                x, y = keypoints[kp_name]
                if 0 <= x < w and 0 <= y < h:
                    # 通道0: x坐标热图
                    heatmap[int(y), int(x), idx * 3] = 1.0
                    # 通道1: y坐标热图
                    heatmap[int(y), int(x), idx * 3 + 1] = 1.0
                    # 通道2: confidence（置信度）
                    heatmap[int(y), int(x), idx * 3 + 2] = 1.0
        
        # 转换为PIL Image（需要转换为uint8）
        # 将51通道转换为RGB显示（仅用于可视化，实际训练时使用51通道）
        # 但为了兼容性，我们返回一个3通道的RGB图像，然后在transform时处理
        pose_img_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 绘制骨架用于可视化
        connections = [
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_elbow'),
            ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'),
            ('right_elbow', 'right_wrist'),
            ('left_shoulder', 'left_hip'),
            ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            ('left_hip', 'left_knee'),
            ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'),
            ('right_knee', 'right_ankle'),
        ]
        
        for start, end in connections:
            if start in keypoints and end in keypoints:
                pt1 = (int(keypoints[start][0]), int(keypoints[start][1]))
                pt2 = (int(keypoints[end][0]), int(keypoints[end][1]))
                cv2.line(pose_img_rgb, pt1, pt2, (255, 255, 255), 2)
        
        for kp_name, (x, y) in keypoints.items():
            cv2.circle(pose_img_rgb, (int(x), int(y)), 5, (255, 255, 255), -1)
        
        return Image.fromarray(pose_img_rgb)
    
    def _convert_to_pose_heatmap(self, keypoints: Dict, img_size: tuple) -> torch.Tensor:
        """将关键点转换为51通道热图tensor"""
        h, w = img_size
        
        # COCO格式的17个关键点顺序
        coco_keypoints = [
            'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
        ]
        
        # 创建51通道热图（17个关键点 * 3）
        heatmap = np.zeros((51, h, w), dtype=np.float32)
        sigma = 10.0  # 高斯核标准差
        
        for idx, kp_name in enumerate(coco_keypoints):
            if kp_name in keypoints:
                x, y = keypoints[kp_name]
                if 0 <= x < w and 0 <= y < h:
                    # 创建高斯热图
                    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
                    gaussian = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma ** 2))
                    
                    # 通道0: x坐标热图
                    heatmap[idx * 3] = gaussian
                    # 通道1: y坐标热图
                    heatmap[idx * 3 + 1] = gaussian
                    # 通道2: confidence（置信度）
                    heatmap[idx * 3 + 2] = gaussian
        
        return torch.from_numpy(heatmap).float()

