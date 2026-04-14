"""
注意力机制模块
在关键帧过渡中，注意力机制通过动态分配权重，聚焦于对当前生成帧影响较大的历史帧或未来帧
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional


class AttentionModule(nn.Module):
    """注意力机制模块"""
    
    def __init__(self,
                 input_dim: int = 256,
                 num_heads: int = 8,
                 dropout: float = 0.1):
        """
        初始化注意力模块
        
        Args:
            input_dim: 输入维度
            num_heads: 注意力头数
            dropout: Dropout比率
        """
        super().__init__()
        
        assert input_dim % num_heads == 0, "input_dim必须能被num_heads整除"
        
        self.input_dim = input_dim
        self.num_heads = num_heads
        self.head_dim = input_dim // num_heads
        self.scale = math.sqrt(self.head_dim)
        
        # Query, Key, Value投影
        self.q_proj = nn.Linear(input_dim, input_dim)
        self.k_proj = nn.Linear(input_dim, input_dim)
        self.v_proj = nn.Linear(input_dim, input_dim)
        
        # 输出投影
        self.out_proj = nn.Linear(input_dim, input_dim)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
    
    def forward(self,
               query: torch.Tensor,
               key: torch.Tensor,
               value: torch.Tensor,
               mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        前向传播
        
        Args:
            query: Query张量 [B, T_q, D]
            key: Key张量 [B, T_k, D]
            value: Value张量 [B, T_v, D]
            mask: 注意力掩码 [B, T_q, T_k]（可选）
            
        Returns:
            注意力输出 [B, T_q, D]
        """
        B, T_q, D = query.size()
        T_k = key.size(1)
        T_v = value.size(1)
        
        # 投影到Q, K, V
        Q = self.q_proj(query).view(B, T_q, self.num_heads, self.head_dim).transpose(1, 2)  # [B, H, T_q, d]
        K = self.k_proj(key).view(B, T_k, self.num_heads, self.head_dim).transpose(1, 2)  # [B, H, T_k, d]
        V = self.v_proj(value).view(B, T_v, self.num_heads, self.head_dim).transpose(1, 2)  # [B, H, T_v, d]
        
        # 计算注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) / self.scale  # [B, H, T_q, T_k]
        
        # 应用掩码
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1) == 0, float('-inf'))
        
        # Softmax
        attn_weights = F.softmax(scores, dim=-1)  # [B, H, T_q, T_k]
        attn_weights = self.dropout(attn_weights)
        
        # 应用注意力权重
        attn_output = torch.matmul(attn_weights, V)  # [B, H, T_q, d]
        
        # 合并多头
        attn_output = attn_output.transpose(1, 2).contiguous().view(B, T_q, D)  # [B, T_q, D]
        
        # 输出投影
        output = self.out_proj(attn_output)
        
        return output


class TemporalAttention(nn.Module):
    """时间注意力模块 - 用于关键帧过渡"""
    
    def __init__(self,
                 input_dim: int = 256,
                 num_heads: int = 8,
                 lookback: int = 5,
                 lookahead: int = 5):
        """
        初始化时间注意力模块
        
        Args:
            input_dim: 输入维度
            num_heads: 注意力头数
            lookback: 回看帧数
            lookahead: 前瞻帧数
        """
        super().__init__()
        
        self.lookback = lookback
        self.lookahead = lookahead
        
        self.attention = AttentionModule(input_dim, num_heads)
        
        # 位置编码
        self.pos_encoding = nn.Parameter(
            torch.randn(lookback + lookahead + 1, input_dim)
        )
    
    def forward(self, 
               current_frame: torch.Tensor,
               history_frames: torch.Tensor,
               future_frames: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        前向传播
        
        Args:
            current_frame: 当前帧 [B, D]
            history_frames: 历史帧 [B, T_h, D]
            future_frames: 未来帧 [B, T_f, D]（可选）
            
        Returns:
            增强的当前帧 [B, D]
        """
        B, D = current_frame.size()
        
        # 准备上下文
        context_frames = [history_frames]
        if future_frames is not None:
            context_frames.append(future_frames)
        
        context = torch.cat(context_frames, dim=1)  # [B, T_h+T_f, D]
        
        # 添加位置编码
        T_context = context.size(1)
        if T_context <= len(self.pos_encoding):
            pos_enc = self.pos_encoding[:T_context]
            context = context + pos_enc.unsqueeze(0)
        
        # 当前帧作为query
        query = current_frame.unsqueeze(1)  # [B, 1, D]
        
        # 注意力计算
        enhanced_frame = self.attention(query, context, context)  # [B, 1, D]
        
        return enhanced_frame.squeeze(1)  # [B, D]








