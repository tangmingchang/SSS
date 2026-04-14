"""皮影数据集 - 参考Moore-AnimateAnyone实现"""
import json
import random
import torch
import torchvision.transforms as transforms
from PIL import Image
from torch.utils.data import Dataset
from pathlib import Path
from typing import List, Dict
import cv2
import numpy as np


class PiyingDataset(Dataset):
    """皮影数据集 - 用于训练"""
    
    def __init__(
        self,
        img_size=(512, 768),
        img_scale=(0.9, 1.0),
        data_meta_paths: List[str] = None,
        sample_margin: int = 10,
        characters_dir: str = None,
    ):
        self.img_size = img_size
        self.img_scale = img_scale
        self.sample_margin = sample_margin
        
        # 加载元数据
        self.vid_meta = []
        if data_meta_paths:
            for meta_path in data_meta_paths:
                if Path(meta_path).exists():
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.vid_meta.extend(data)
                        elif 'samples' in data:
                            self.vid_meta.extend(data['samples'])
        
        # 如果没有视频数据，使用图层数据
        if not self.vid_meta and characters_dir:
            self._load_from_layers(characters_dir)
        
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
    
    def _load_from_layers(self, characters_dir: str):
        """从图层数据创建训练样本"""
        from src.layers import LayerLoader, LayerComposer
        
        loader = LayerLoader()
        composer = LayerComposer(loader)
        chars_dir = Path(characters_dir)
        
        for char_dir in chars_dir.iterdir():
            if not char_dir.is_dir():
                continue
            try:
                layers = loader.load_character(str(char_dir))
                composed = composer.compose(layers)
                
                # 转换为RGB
                if composed.shape[2] == 4:
                    alpha = composed[:, :, 3:4] / 255.0
                    rgb = composed[:, :, :3]
                    composed_rgb = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
                else:
                    composed_rgb = composed[:, :, :3]
                
                # 保存临时图像
                temp_img = Path(characters_dir) / f"{char_dir.name}_temp.png"
                cv2.imwrite(str(temp_img), composed_rgb)
                
                self.vid_meta.append({
                    'character_name': char_dir.name,
                    'reference_image': str(temp_img),
                    'video_path': None,
                    'kps_path': None,
                    'layers': list(layers.keys())
                })
            except Exception as e:
                print(f"跳过 {char_dir.name}: {e}")
    
    def __getitem__(self, index):
        meta = self.vid_meta[index]
        
        # 如果有视频，使用视频数据
        if meta.get('video_path') and Path(meta['video_path']).exists():
            return self._get_video_sample(meta)
        else:
            # 使用图层数据
            return self._get_layer_sample(meta)
    
    def _get_video_sample(self, meta):
        """从视频获取样本"""
        from decord import VideoReader
        
        video_path = meta['video_path']
        kps_path = meta.get('kps_path')
        
        video_reader = VideoReader(video_path)
        video_length = len(video_reader)
        
        margin = min(self.sample_margin, video_length)
        ref_idx = random.randint(0, video_length - 1)
        
        if ref_idx + margin < video_length:
            tgt_idx = random.randint(ref_idx + margin, video_length - 1)
        elif ref_idx - margin > 0:
            tgt_idx = random.randint(0, ref_idx - margin)
        else:
            tgt_idx = random.randint(0, video_length - 1)
        
        ref_img = Image.fromarray(video_reader[ref_idx].asnumpy())
        tgt_img = Image.fromarray(video_reader[tgt_idx].asnumpy())
        
        # 姿态图像
        if kps_path and Path(kps_path).exists():
            kps_reader = VideoReader(kps_path)
            tgt_pose = Image.fromarray(kps_reader[tgt_idx].asnumpy())
        else:
            # 生成姿态图
            from src.pose import PoseDetector
            detector = PoseDetector()
            tgt_array = np.array(tgt_img)
            keypoints = detector.detect(tgt_array)
            tgt_pose = self._keypoints_to_image(keypoints, tgt_array.shape[:2])
        
        state = torch.get_rng_state()
        tgt_img_tensor = self.transform(tgt_img)
        tgt_pose_tensor = self.cond_transform(tgt_pose)
        ref_img_tensor = self.transform(ref_img)
        
        return {
            'img': tgt_img_tensor,
            'tgt_pose': tgt_pose_tensor,
            'ref_img': ref_img_tensor,
            'clip_images': ref_img_tensor,  # 简化：使用相同图像
        }
    
    def _get_layer_sample(self, meta):
        """从图层获取样本"""
        ref_img_path = meta.get('reference_image')
        if not ref_img_path or not Path(ref_img_path).exists():
            # 从图层重新生成
            from src.layers import LayerLoader, LayerComposer
            loader = LayerLoader()
            composer = LayerComposer(loader)
            
            char_name = meta.get('character_name', 'unknown')
            chars_dir = Path(ref_img_path).parent if ref_img_path else Path("data/characters")
            char_dir = chars_dir / char_name
            
            layers = loader.load_character(str(char_dir))
            composed = composer.compose(layers)
            
            if composed.shape[2] == 4:
                alpha = composed[:, :, 3:4] / 255.0
                rgb = composed[:, :, :3]
                composed_rgb = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
            else:
                composed_rgb = composed[:, :, :3]
            
            ref_img = Image.fromarray(composed_rgb)
        else:
            ref_img = Image.open(ref_img_path).convert('RGB')
        
        # 生成目标图像（添加随机变换）
        tgt_img = ref_img.copy()
        
        # 生成姿态图
        from src.pose import PoseDetector
        detector = PoseDetector()
        ref_array = np.array(ref_img)
        keypoints = detector.detect(ref_array)
        tgt_pose = self._keypoints_to_image(keypoints, ref_array.shape[:2])
        
        state = torch.get_rng_state()
        tgt_img_tensor = self.transform(tgt_img)
        tgt_pose_tensor = self.cond_transform(tgt_pose)
        ref_img_tensor = self.transform(ref_img)
        
        return {
            'img': tgt_img_tensor,
            'tgt_pose': tgt_pose_tensor,
            'ref_img': ref_img_tensor,
            'clip_images': ref_img_tensor,
        }
    
    def _keypoints_to_image(self, keypoints: Dict, img_shape: tuple) -> Image.Image:
        """将关键点转换为图像"""
        h, w = img_shape[:2]
        pose_img = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 绘制关键点
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
                cv2.line(pose_img, pt1, pt2, (255, 255, 255), 2)
        
        for kp_name, (x, y) in keypoints.items():
            cv2.circle(pose_img, (int(x), int(y)), 5, (255, 255, 255), -1)
        
        return Image.fromarray(pose_img)
    
    def __len__(self):
        return len(self.vid_meta)








