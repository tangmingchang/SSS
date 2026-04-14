"""统一数据集包装器 - 将不同格式的数据集统一为相同格式"""
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset
from typing import Dict, Any
from PIL import Image
import numpy as np
import torchvision.transforms as transforms


class UnifiedDatasetWrapper(Dataset):
    """统一数据集包装器，将不同格式的数据集转换为统一格式"""
    
    def __init__(self, dataset: Dataset, dataset_type: str = 'auto', img_size=(512, 768)):
        """
        包装数据集，统一返回格式
        
        Args:
            dataset: 原始数据集
            dataset_type: 数据集类型 ('layer', 'hasper', 'yale', 'auto')
            img_size: 图像尺寸
        """
        self.dataset = dataset
        self.dataset_type = dataset_type
        self.img_size = img_size
        
        # 姿态检测器（用于生成姿态图）
        from src.pose import PoseDetector
        self.pose_detector = PoseDetector()
        
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
        return len(self.dataset)
    
    def __getitem__(self, idx):
        sample = self.dataset[idx]
        
        # 根据数据集类型转换
        if 'img' in sample and 'ref_img' in sample and 'tgt_pose' in sample:
            # LayerDataset格式 - 已经是统一格式
            return {
                'img': sample['img'],
                'ref_img': sample['ref_img'],
                'tgt_pose': sample['tgt_pose'],
                'clip_images': sample.get('clip_images', sample['ref_img']),
                'source': 'layer'
            }
        elif 'image' in sample:
            # HASPER或Yale格式 - 需要转换
            img_tensor = sample['image']
            
            # 优先使用原始图像路径（效率更高）
            if 'image_path' in sample:
                # 从路径加载图像检测姿态
                try:
                    img_pil = Image.open(sample['image_path']).convert('RGB')
                    img_np = np.array(img_pil)
                except:
                    # 如果路径加载失败，使用tensor转换
                    img_pil = self._tensor_to_pil(img_tensor)
                    img_np = np.array(img_pil)
            else:
                # 从tensor转换（效率较低）
                img_pil = self._tensor_to_pil(img_tensor)
                img_np = np.array(img_pil)
            
            # 检测关键点并生成姿态图
            keypoints = self.pose_detector.detect(img_np)
            h, w = img_np.shape[:2]
            pose_tensor = self._convert_to_pose_heatmap(keypoints, (h, w))
            
            # 调整尺寸以匹配img_tensor
            if pose_tensor.shape[-2:] != img_tensor.shape[-2:]:
                pose_tensor = F.interpolate(
                    pose_tensor.unsqueeze(0),
                    size=img_tensor.shape[-2:],
                    mode='bilinear',
                    align_corners=False
                ).squeeze(0)
            
            return {
                'img': img_tensor,
                'ref_img': img_tensor,
                'tgt_pose': pose_tensor,
                'clip_images': img_tensor,
                'source': 'hasper' if 'label' in sample else 'yale'
            }
        else:
            raise ValueError(f"未知的数据格式: {sample.keys()}")
    
    def _tensor_to_pil(self, tensor):
        """将tensor转换为PIL图像"""
        # 确保tensor在CPU上
        if tensor.is_cuda:
            tensor = tensor.cpu()
        
        # 反归一化
        tensor = tensor * 0.5 + 0.5
        tensor = torch.clamp(tensor, 0, 1)
        
        # 转换为numpy
        if tensor.dim() == 4:
            tensor = tensor[0]
        if tensor.dim() == 3:
            img_np = tensor.permute(1, 2, 0).numpy()
        else:
            img_np = tensor.numpy()
        
        # 确保是uint8格式
        if img_np.max() <= 1.0:
            img_np = (img_np * 255).astype(np.uint8)
        else:
            img_np = img_np.astype(np.uint8)
        
        # 确保是RGB格式
        if len(img_np.shape) == 2:
            img_np = np.stack([img_np] * 3, axis=2)
        elif img_np.shape[2] == 1:
            img_np = np.repeat(img_np, 3, axis=2)
        
        return Image.fromarray(img_np)
    
    def _keypoints_to_image(self, keypoints: Dict, img_shape: tuple) -> Image.Image:
        """将关键点转换为图像"""
        h, w = img_shape[:2]
        pose_img = np.zeros((h, w, 3), dtype=np.uint8)
        
        import cv2
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
    
    def _convert_to_pose_heatmap(self, keypoints: Dict, img_shape: tuple) -> torch.Tensor:
        """将关键点转换为51通道热图tensor"""
        h, w = img_shape[:2]
        
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


def unified_collate_fn(batch):
    """统一的数据批处理函数"""
    if not batch:
        return {}
    
    # 收集所有可能的键
    all_keys = set()
    for item in batch:
        all_keys.update(item.keys())
    
    # 为每个样本补充缺失的键
    normalized_batch = []
    for item in batch:
        normalized_item = item.copy()
        for key in all_keys:
            if key not in normalized_item:
                if key == 'source':
                    normalized_item[key] = 'unknown'
                elif key == 'character':
                    normalized_item[key] = ''
                elif key in ['img', 'ref_img', 'tgt_pose', 'clip_images']:
                    # 对于必需的tensor键，使用ref_img或img作为默认值
                    if 'ref_img' in normalized_item:
                        normalized_item[key] = normalized_item['ref_img']
                    elif 'img' in normalized_item:
                        normalized_item[key] = normalized_item['img']
                    else:
                        # 如果都没有，跳过这个键
                        continue
        normalized_batch.append(normalized_item)
    
    # 使用默认collate
    from torch.utils.data._utils.collate import default_collate
    try:
        return default_collate(normalized_batch)
    except Exception as e:
        # 如果默认collate失败，手动处理
        result = {}
        for key in all_keys:
            values = []
            for item in normalized_batch:
                if key in item:
                    values.append(item[key])
            
            if not values:
                continue
                
            if isinstance(values[0], torch.Tensor):
                try:
                    result[key] = torch.stack(values)
                except:
                    result[key] = values  # 如果无法stack，保持列表
            elif isinstance(values[0], (list, tuple)):
                result[key] = values
            elif isinstance(values[0], str):
                result[key] = values
            else:
                result[key] = values
        return result

