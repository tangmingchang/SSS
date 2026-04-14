"""
双向LSTM动作生成模型
通过前向和后向两个时间维度捕捉动作序列的长期依赖关系
"""

import torch
import torch.nn as nn
from typing import Optional, Tuple


class BidirectionalLSTMActionModel(nn.Module):
    """双向LSTM动作生成模型"""
    
    def __init__(self,
                 input_dim: int = 21 * 3,  # 输入维度（关键点数量 * 坐标维度）
                 hidden_dim: int = 256,
                 num_layers: int = 2,
                 dropout: float = 0.1):
        """
        初始化双向LSTM模型
        
        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            num_layers: LSTM层数
            dropout: Dropout比率
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # 双向LSTM
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # 输出投影层
        # 双向LSTM输出维度是 hidden_dim * 2
        self.output_proj = nn.Linear(hidden_dim * 2, input_dim)
        
        # Dropout层
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, 
               x: torch.Tensor,
               hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None) -> Tuple[torch.Tensor, Tuple]:
        """
        前向传播
        
        Args:
            x: 输入张量 [B, T, D]
               B: batch size, T: 时间步, D: 输入维度
            hidden: 初始隐藏状态（可选）
            
        Returns:
            output: 输出张量 [B, T, D]
            hidden: 最终隐藏状态
        """
        # LSTM前向传播
        lstm_out, hidden = self.lstm(x, hidden)  # [B, T, hidden_dim*2]
        
        # Dropout
        lstm_out = self.dropout(lstm_out)
        
        # 输出投影
        output = self.output_proj(lstm_out)  # [B, T, input_dim]
        
        return output, hidden
    
    def generate(self,
                initial_pose: torch.Tensor,
                target_length: int,
                hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None) -> torch.Tensor:
        """
        生成动作序列
        
        Args:
            initial_pose: 初始姿态 [B, D] 或 [B, 1, D]
            target_length: 目标序列长度
            hidden: 初始隐藏状态（可选）
            
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
        for _ in range(target_length - 1):
            # 前向传播
            output, hidden = self.forward(current_input, hidden)
            
            # 使用最后一个时间步的输出作为下一个输入
            next_frame = output[:, -1:, :]  # [B, 1, D]
            generated_sequence.append(next_frame)
            
            current_input = next_frame
        
        # 拼接所有帧
        generated = torch.cat(generated_sequence, dim=1)  # [B, target_length, D]
        
        return generated








