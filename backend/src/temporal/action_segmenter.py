"""
动作分段器 - 对动作数据进行逐帧分析，识别动作边界，划分出具有语义连贯性的片段
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
try:
    from .tsm_model import ActionBoundaryDetector
except ImportError:
    # 如果TSM模型不存在，创建一个简化版本
    import torch.nn as nn
    class ActionBoundaryDetector(nn.Module):
        def __init__(self):
            super().__init__()
            self.classifier = nn.Linear(51, 2)  # 简化版本
        def forward(self, x):
            return torch.softmax(self.classifier(x), dim=-1)


class ActionSegmenter:
    """动作分段器"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化动作分段器
        
        Args:
            model_path: 预训练模型路径（可选）
        """
        self.boundary_detector = ActionBoundaryDetector()
        if model_path:
            self.boundary_detector.load_state_dict(torch.load(model_path))
        self.boundary_detector.eval()
    
    def segment(self, 
               action_sequence: np.ndarray,
               min_segment_length: int = 10) -> List[Dict]:
        """
        对动作序列进行分段
        
        Args:
            action_sequence: 动作序列 [T, J*3] 或 [T, J, 3]
            min_segment_length: 最小片段长度
            
        Returns:
            分段列表，每个元素包含：
            - start_frame: 起始帧
            - end_frame: 结束帧
            - segment_data: 片段数据
        """
        # 转换为张量
        if action_sequence.ndim == 3:
            # [T, J, 3] -> [T, J*3]
            T, J, D = action_sequence.shape
            action_sequence = action_sequence.reshape(T, J * D)
        
        T, D = action_sequence.shape
        
        # 转换为torch张量
        x = torch.from_numpy(action_sequence).float().unsqueeze(0)  # [1, T, D]
        
        # 检测边界
        with torch.no_grad():
            boundary_probs = self.boundary_detector(x)  # [1, T, 2]
            boundaries = boundary_probs[0, :, 1] > 0.5  # 边界概率 > 0.5
        
        # 找到边界位置
        boundary_indices = np.where(boundaries.numpy())[0].tolist()
        
        # 如果没有检测到边界，返回整个序列
        if not boundary_indices:
            return [{
                'start_frame': 0,
                'end_frame': T - 1,
                'segment_data': action_sequence
            }]
        
        # 添加起始和结束
        if boundary_indices[0] != 0:
            boundary_indices.insert(0, 0)
        if boundary_indices[-1] != T - 1:
            boundary_indices.append(T - 1)
        
        # 生成分段
        segments = []
        for i in range(len(boundary_indices) - 1):
            start = boundary_indices[i]
            end = boundary_indices[i + 1]
            
            # 检查最小长度
            if end - start >= min_segment_length:
                segments.append({
                    'start_frame': start,
                    'end_frame': end,
                    'segment_data': action_sequence[start:end+1]
                })
        
        return segments
    
    def assign_semantic_labels(self, 
                              segments: List[Dict],
                              action_library: Dict[str, np.ndarray]) -> List[Dict]:
        """
        为分段分配语义标签
        
        Args:
            segments: 动作分段列表
            action_library: 动作库字典，键为动作名称，值为动作模板
            
        Returns:
            带语义标签的分段列表
        """
        labeled_segments = []
        
        for segment in segments:
            segment_data = segment['segment_data']
            
            # 计算与动作库中每个动作的相似度
            best_match = None
            best_score = -1
            
            for action_name, action_template in action_library.items():
                # 计算相似度（简化：使用余弦相似度）
                score = self._compute_similarity(segment_data, action_template)
                
                if score > best_score:
                    best_score = score
                    best_match = action_name
            
            # 添加语义标签
            segment['semantic_label'] = best_match
            segment['confidence'] = best_score
            labeled_segments.append(segment)
        
        return labeled_segments
    
    def _compute_similarity(self, 
                           segment: np.ndarray,
                           template: np.ndarray) -> float:
        """
        计算动作相似度
        
        Args:
            segment: 动作片段
            template: 动作模板
            
        Returns:
            相似度分数 [0, 1]
        """
        # 对齐长度
        min_len = min(len(segment), len(template))
        segment = segment[:min_len]
        template = template[:min_len]
        
        # 展平
        segment_flat = segment.flatten()
        template_flat = template.flatten()
        
        # 归一化
        segment_norm = segment_flat / (np.linalg.norm(segment_flat) + 1e-6)
        template_norm = template_flat / (np.linalg.norm(template_flat) + 1e-6)
        
        # 余弦相似度
        similarity = np.dot(segment_norm, template_norm)
        
        return float(similarity)

