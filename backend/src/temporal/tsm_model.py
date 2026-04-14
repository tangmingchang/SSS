"""
TSM (Temporal Shift Module) 模型
在空间卷积中引入"时间位移"操作，将部分通道特征在时间维度上前移或后移，从而隐式捕捉时序关系
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class TemporalShift(nn.Module):
    """时间位移模块"""
    
    def __init__(self, n_segment: int = 8, n_div: int = 8):
        """
        初始化时间位移模块
        
        Args:
            n_segment: 时间片段数量
            n_div: 位移通道的除数（控制位移通道的比例）
        """
        super().__init__()
        self.n_segment = n_segment
        self.fold_div = n_div
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量 [B, C, T, H, W] 或 [B*T, C, H, W]
            
        Returns:
            位移后的张量
        """
        # 如果输入是5D，需要reshape
        if x.dim() == 5:
            B, C, T, H, W = x.size()
            x = x.view(B * T, C, H, W)
        
        B, C, H, W = x.size()
        fold = C // self.fold_div
        
        # 前向位移和后向位移
        out = torch.zeros_like(x)
        out[:, :-fold] = x[:, fold:]  # 前向位移
        out[:, -fold:] = x[:, :fold]  # 后向位移
        
        return out


class TSMModel(nn.Module):
    """TSM模型 - 用于动作序列的时间建模"""
    
    def __init__(self, 
                 input_dim: int = 21 * 3,  # 21个关键点 * 3维坐标
                 hidden_dim: int = 256,
                 num_layers: int = 3,
                 n_segment: int = 8):
        """
        初始化TSM模型
        
        Args:
            input_dim: 输入维度（关键点数量 * 坐标维度）
            hidden_dim: 隐藏层维度
            num_layers: 层数
            n_segment: 时间片段数量
        """
        super().__init__()
        
        self.n_segment = n_segment
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # 输入投影层
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        
        # TSM卷积层
        layers = []
        for i in range(num_layers):
            layers.extend([
                TemporalShift(n_segment=n_segment),
                nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=1),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(inplace=True)
            ])
        
        self.tsm_layers = nn.Sequential(*layers)
        
        # 输出层
        self.output_proj = nn.Linear(hidden_dim, input_dim)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量 [B, T, J*3] 或 [B*T, J*3]
               B: batch size, T: 时间步, J: 关键点数量
            
        Returns:
            输出张量 [B, T, J*3]
        """
        B, T, D = x.size()
        
        # Reshape为 [B*T, D]
        x = x.view(B * T, D)
        
        # 输入投影
        x = self.input_proj(x)  # [B*T, hidden_dim]
        
        # Reshape为 [B*T, hidden_dim, 1] 用于1D卷积
        x = x.unsqueeze(-1)  # [B*T, hidden_dim, 1]
        
        # TSM层处理
        x = self.tsm_layers(x)  # [B*T, hidden_dim, 1]
        
        # Reshape回 [B*T, hidden_dim]
        x = x.squeeze(-1)
        
        # 输出投影
        x = self.output_proj(x)  # [B*T, input_dim]
        
        # Reshape回 [B, T, D]
        x = x.view(B, T, D)
        
        return x


class ActionBoundaryDetector(nn.Module):
    """动作边界检测器 - 识别动作边界"""
    
    def __init__(self, input_dim: int = 21 * 3, hidden_dim: int = 128):
        """
        初始化动作边界检测器
        
        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
        """
        super().__init__()
        
        self.tsm = TSMModel(input_dim, hidden_dim)
        
        # 边界分类器
        self.boundary_classifier = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 2)  # 边界/非边界
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        检测动作边界
        
        Args:
            x: 输入动作序列 [B, T, D]
            
        Returns:
            边界概率 [B, T, 2]
        """
        # TSM特征提取
        features = self.tsm(x)  # [B, T, input_dim]
        
        # 投影到隐藏维度
        hidden = self.tsm.input_proj(features.mean(dim=-1, keepdim=True).expand_as(features))
        
        # 边界分类
        boundaries = self.boundary_classifier(hidden)
        
        return F.softmax(boundaries, dim=-1)








