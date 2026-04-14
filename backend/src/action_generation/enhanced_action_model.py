"""
增强的动作生成模型
结合双向LSTM、注意力机制和IK物理约束
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple
from .lstm_action_model import BidirectionalLSTMActionModel
try:
    from .attention_module import AttentionModule
except ImportError:
    # 如果注意力模块不存在，创建一个简化版本
    class AttentionModule(nn.Module):
        def __init__(self, input_dim, num_heads=8, dropout=0.1):
            super().__init__()
            self.attention = nn.MultiheadAttention(input_dim, num_heads, dropout=dropout, batch_first=True)
        def forward(self, x):
            out, _ = self.attention(x, x, x)
            return out

from ..models.inverse_kinematics import IKConstraintLayer


class EnhancedActionGenerator(nn.Module):
    """增强的动作生成模型"""
    
    def __init__(self,
                 input_dim: int = 17 * 3,  # 17个关键点 * 3坐标
                 hidden_dim: int = 256,
                 num_layers: int = 2,
                 num_heads: int = 8,
                 dropout: float = 0.1,
                 use_ik_constraint: bool = True):
        """
        初始化增强动作生成模型
        
        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            num_layers: LSTM层数
            num_heads: 注意力头数
            dropout: Dropout比率
            use_ik_constraint: 是否使用IK约束
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.use_ik_constraint = use_ik_constraint
        
        # 双向LSTM编码器
        self.lstm_encoder = BidirectionalLSTMActionModel(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout
        )
        
        # 注意力机制（使用自注意力）
        # 注意：embed_dim需要能被num_heads整除
        attention_dim = (hidden_dim * 2 // num_heads) * num_heads
        self.attention = nn.MultiheadAttention(
            embed_dim=attention_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        # 如果维度不匹配，添加投影层
        if attention_dim != hidden_dim * 2:
            self.attention_proj = nn.Linear(hidden_dim * 2, attention_dim)
            self.attention_proj_back = nn.Linear(attention_dim, hidden_dim * 2)
        else:
            self.attention_proj = None
            self.attention_proj_back = None
        
        # 解码器（LSTM）
        self.decoder_lstm = nn.LSTM(
            input_size=hidden_dim * 2,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # 输出投影层
        self.output_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, input_dim),
            nn.Tanh()  # 归一化到[-1, 1]
        )
        
        # IK约束层（可选）
        if use_ik_constraint:
            self.ik_constraint = IKConstraintLayer()
        else:
            self.ik_constraint = None
    
    def forward(self,
               input_sequence: torch.Tensor,
               target_positions: Optional[torch.Tensor] = None,
               bone_lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        前向传播
        
        Args:
            input_sequence: 输入动作序列 [B, T, D]
            target_positions: 目标位置（用于IK约束）[B, T, 3]
            bone_lengths: 骨骼长度 [B, chain_length]
            
        Returns:
            生成的动作序列 [B, T, D]
        """
        B, T, D = input_sequence.shape
        
        # LSTM编码
        encoded, hidden = self.lstm_encoder(input_sequence)  # [B, T, hidden_dim*2]
        
        # 确保encoded的维度正确
        if encoded.shape[-1] != self.hidden_dim * 2:
            # 如果维度不匹配，添加投影层
            if not hasattr(self, 'dim_fix_proj'):
                self.dim_fix_proj = nn.Linear(encoded.shape[-1], self.hidden_dim * 2).to(encoded.device)
            encoded = self.dim_fix_proj(encoded)
        
        # 注意力机制（自注意力）
        if self.attention_proj is not None:
            encoded_proj = self.attention_proj(encoded)
            attended_proj, _ = self.attention(encoded_proj, encoded_proj, encoded_proj)
            attended = self.attention_proj_back(attended_proj)
        else:
            attended, _ = self.attention(encoded, encoded, encoded)  # [B, T, hidden_dim*2]
        
        # 解码
        decoded, _ = self.decoder_lstm(attended)  # [B, T, hidden_dim]
        
        # 输出投影
        output = self.output_proj(decoded)  # [B, T, input_dim]
        
        # 应用IK约束（如果启用）
        if self.use_ik_constraint and target_positions is not None and bone_lengths is not None:
            output = self.ik_constraint(output, target_positions, bone_lengths)
        
        return output
    
    def generate(self,
                initial_pose: torch.Tensor,
                target_length: int,
                target_positions: Optional[torch.Tensor] = None,
                bone_lengths: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        生成动作序列
        
        Args:
            initial_pose: 初始姿态 [B, D] 或 [B, 1, D]
            target_length: 目标序列长度
            target_positions: 目标位置序列 [B, target_length, 3]
            bone_lengths: 骨骼长度 [B, chain_length]
            
        Returns:
            生成的动作序列 [B, target_length, D]
        """
        if initial_pose.dim() == 2:
            initial_pose = initial_pose.unsqueeze(1)  # [B, 1, D]
        
        B = initial_pose.size(0)
        D = initial_pose.size(2)
        
        # 初始化序列
        generated_sequence = [initial_pose]
        current_input = initial_pose
        
        # 逐步生成
        for t in range(target_length - 1):
            # 前向传播
            output = self.forward(
                current_input,
                target_positions[:, t:t+1] if target_positions is not None else None,
                bone_lengths
            )
            
            # 使用最后一个时间步的输出作为下一个输入
            next_frame = output[:, -1:, :]  # [B, 1, D]
            generated_sequence.append(next_frame)
            
            current_input = torch.cat([current_input, next_frame], dim=1)
            # 保持序列长度（滑动窗口）
            if current_input.size(1) > 10:
                current_input = current_input[:, -10:]
        
        # 拼接所有帧
        generated = torch.cat(generated_sequence, dim=1)  # [B, target_length, D]
        
        return generated

