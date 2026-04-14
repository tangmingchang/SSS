"""
姿态引导模块 - 用于将骨骼信号转换为控制信号
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Tuple


class PoseGuider(nn.Module):
    """姿态引导模块"""
    
    def __init__(self, in_channels: int = 17 * 3,  # 17个关键点，每个3维(x, y, confidence)
                 out_channels: int = 256,
                 block_out_channels: Tuple[int, ...] = (64, 128, 256)):
        """
        初始化姿态引导模块
        
        Args:
            in_channels: 输入通道数（关键点数量 * 维度）
            out_channels: 输出通道数
            block_out_channels: 各块的输出通道数
        """
        super().__init__()
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        
        # 构建编码器（确保输出尺寸与ref_encoder匹配）
        # ref_encoder: 512x768 -> 256x384 -> 128x192
        # 我们需要pose_guider也输出类似尺寸
        
        layers = []
        in_ch = in_channels
        
        # 第一层：降采样到256x384，通道数64
        layers.extend([
            nn.Conv2d(in_ch, block_out_channels[0], kernel_size=3, padding=1, stride=2),
            nn.BatchNorm2d(block_out_channels[0]),
            nn.ReLU(inplace=True),
        ])
        in_ch = block_out_channels[0]
        
        # 第二层：降采样到128x192，通道数128（匹配ref_encoder）
        layers.extend([
            nn.Conv2d(in_ch, block_out_channels[1], kernel_size=3, padding=1, stride=2),
            nn.BatchNorm2d(block_out_channels[1]),
            nn.ReLU(inplace=True),
        ])
        in_ch = block_out_channels[1]
        
        # 第三层：不降采样，增加通道数到256
        layers.extend([
            nn.Conv2d(in_ch, block_out_channels[2], kernel_size=3, padding=1),
            nn.BatchNorm2d(block_out_channels[2]),
            nn.ReLU(inplace=True),
        ])
        in_ch = block_out_channels[2]
        
        # 最终投影层（不改变尺寸）
        layers.append(
            nn.Conv2d(in_ch, out_channels, kernel_size=1)
        )
        
        self.encoder = nn.Sequential(*layers)
    
    def forward(self, skeleton_features: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            skeleton_features: 骨骼特征张量 [B, C, H, W]
            
        Returns:
            引导特征 [B, out_channels, H', W']
        """
        return self.encoder(skeleton_features)
    
    def process_skeleton(self, skeleton: Dict, 
                        image_size: Tuple[int, int] = (512, 768)) -> torch.Tensor:
        """
        处理骨骼信号，转换为特征图
        
        Args:
            skeleton: 骨骼信号字典
            image_size: 图像尺寸 (width, height)
            
        Returns:
            特征图张量
        """
        # 从骨骼信号中提取关键点
        keypoints = skeleton.get('keypoints', {})
        
        # 创建关键点热图
        heatmap = self._create_heatmap(keypoints, image_size)
        
        # 转换为张量
        heatmap_tensor = torch.from_numpy(heatmap).float()
        if heatmap_tensor.dim() == 2:
            heatmap_tensor = heatmap_tensor.unsqueeze(0)
        if heatmap_tensor.dim() == 3:
            heatmap_tensor = heatmap_tensor.unsqueeze(0)
        
        # 调整通道数以匹配输入要求
        # 如果关键点数量不足，进行填充或重复
        current_channels = heatmap_tensor.shape[1]
        if current_channels < self.in_channels:
            padding = torch.zeros(
                heatmap_tensor.shape[0],
                self.in_channels - current_channels,
                heatmap_tensor.shape[2],
                heatmap_tensor.shape[3]
            )
            heatmap_tensor = torch.cat([heatmap_tensor, padding], dim=1)
        elif current_channels > self.in_channels:
            heatmap_tensor = heatmap_tensor[:, :self.in_channels]
        
        return heatmap_tensor
    
    def _create_heatmap(self, keypoints: Dict[str, Tuple[float, float]],
                       image_size: Tuple[int, int],
                       sigma: float = 10.0) -> np.ndarray:
        """
        创建关键点热图
        
        Args:
            keypoints: 关键点字典
            image_size: 图像尺寸 (width, height)
            sigma: 高斯核标准差
            
        Returns:
            热图数组 [num_keypoints, height, width]
        """
        width, height = image_size
        num_keypoints = len(keypoints)
        
        heatmaps = np.zeros((num_keypoints, height, width), dtype=np.float32)
        
        for idx, (name, (x, y)) in enumerate(keypoints.items()):
            if x > 0 and y > 0:  # 有效的关键点
                # 创建高斯热图
                xx, yy = np.meshgrid(np.arange(width), np.arange(height))
                gaussian = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma ** 2))
                heatmaps[idx] = gaussian
        
        return heatmaps

