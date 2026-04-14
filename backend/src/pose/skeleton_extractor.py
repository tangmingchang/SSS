"""
骨骼提取器 - 从关键点中提取骨骼信号
"""

import numpy as np
from typing import Dict, List, Tuple
from .pose_detector import PoseDetector


class SkeletonExtractor:
    """骨骼信号提取器"""
    
    def __init__(self):
        """初始化骨骼提取器"""
        # 定义骨骼连接关系
        self.bone_connections = [
            # 头部
            ("nose", "neck"),
            # 躯干
            ("neck", "left_shoulder"),
            ("neck", "right_shoulder"),
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_hip"),
            ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            # 左臂
            ("left_shoulder", "left_elbow"),
            ("left_elbow", "left_wrist"),
            # 右臂
            ("right_shoulder", "right_elbow"),
            ("right_elbow", "right_wrist"),
            # 左腿
            ("left_hip", "left_knee"),
            ("left_knee", "left_ankle"),
            # 右腿
            ("right_hip", "right_knee"),
            ("right_knee", "right_ankle"),
        ]
    
    def extract_skeleton(self, keypoints: Dict[str, Tuple[float, float]]) -> Dict:
        """
        从关键点提取骨骼信号
        
        Args:
            keypoints: 关键点字典
            
        Returns:
            骨骼信号字典，包含骨骼向量、角度等信息
        """
        skeleton = {
            'keypoints': keypoints,
            'bones': {},
            'angles': {},
            'bone_vectors': {}
        }
        
        # 提取骨骼向量
        for start_name, end_name in self.bone_connections:
            if start_name in keypoints and end_name in keypoints:
                start_pos = np.array(keypoints[start_name])
                end_pos = np.array(keypoints[end_name])
                
                bone_vector = end_pos - start_pos
                bone_length = np.linalg.norm(bone_vector)
                bone_angle = np.arctan2(bone_vector[1], bone_vector[0])
                
                bone_key = f"{start_name}_{end_name}"
                skeleton['bones'][bone_key] = {
                    'start': start_name,
                    'end': end_name,
                    'length': bone_length,
                    'vector': bone_vector.tolist()
                }
                
                skeleton['bone_vectors'][bone_key] = bone_vector.tolist()
                skeleton['angles'][bone_key] = bone_angle
        
        return skeleton
    
    def extract_spatial_aligned_skeleton(self, 
                                        source_keypoints: Dict[str, Tuple[float, float]],
                                        target_keypoints: Dict[str, Tuple[float, float]]) -> Dict:
        """
        提取空间对齐的骨骼信号（用于动画生成）
        
        Args:
            source_keypoints: 源图像的关键点
            target_keypoints: 目标视频帧的关键点
            
        Returns:
            对齐后的骨骼信号
        """
        # 计算空间对齐变换
        transform = self._compute_alignment_transform(source_keypoints, target_keypoints)
        
        # 提取源骨骼
        source_skeleton = self.extract_skeleton(source_keypoints)
        
        # 提取目标骨骼
        target_skeleton = self.extract_skeleton(target_keypoints)
        
        # 应用对齐变换
        aligned_skeleton = {
            'source': source_skeleton,
            'target': target_skeleton,
            'transform': transform,
            'aligned_bones': self._align_bones(source_skeleton, target_skeleton, transform)
        }
        
        return aligned_skeleton
    
    def _compute_alignment_transform(self,
                                    source_keypoints: Dict[str, Tuple[float, float]],
                                    target_keypoints: Dict[str, Tuple[float, float]]) -> Dict:
        """
        计算空间对齐变换
        
        Args:
            source_keypoints: 源关键点
            target_keypoints: 目标关键点
            
        Returns:
            变换参数字典
        """
        # 使用躯干中心点作为对齐参考
        if "left_shoulder" in source_keypoints and "right_shoulder" in source_keypoints:
            source_center = (
                (source_keypoints["left_shoulder"][0] + source_keypoints["right_shoulder"][0]) / 2,
                (source_keypoints["left_shoulder"][1] + source_keypoints["right_shoulder"][1]) / 2
            )
        else:
            source_center = (0, 0)
        
        if "left_shoulder" in target_keypoints and "right_shoulder" in target_keypoints:
            target_center = (
                (target_keypoints["left_shoulder"][0] + target_keypoints["right_shoulder"][0]) / 2,
                (target_keypoints["left_shoulder"][1] + target_keypoints["right_shoulder"][1]) / 2
            )
        else:
            target_center = (0, 0)
        
        # 计算平移
        translation = (
            target_center[0] - source_center[0],
            target_center[1] - source_center[1]
        )
        
        # 计算缩放（基于肩宽）
        if ("left_shoulder" in source_keypoints and "right_shoulder" in source_keypoints and
            "left_shoulder" in target_keypoints and "right_shoulder" in target_keypoints):
            source_width = abs(source_keypoints["right_shoulder"][0] - source_keypoints["left_shoulder"][0])
            target_width = abs(target_keypoints["right_shoulder"][0] - target_keypoints["left_shoulder"][0])
            scale = target_width / source_width if source_width > 0 else 1.0
        else:
            scale = 1.0
        
        return {
            'translation': translation,
            'scale': scale,
            'rotation': 0.0  # 可以添加旋转计算
        }
    
    def _align_bones(self, source_skeleton: Dict, target_skeleton: Dict, 
                    transform: Dict) -> Dict:
        """对齐骨骼信号"""
        aligned = {}
        
        for bone_key in source_skeleton['bone_vectors']:
            if bone_key in target_skeleton['bone_vectors']:
                source_vector = np.array(source_skeleton['bone_vectors'][bone_key])
                target_vector = np.array(target_skeleton['bone_vectors'][bone_key])
                
                # 应用缩放
                aligned_vector = source_vector * transform['scale']
                
                aligned[bone_key] = {
                    'source': source_vector.tolist(),
                    'target': target_vector.tolist(),
                    'aligned': aligned_vector.tolist(),
                    'motion': (target_vector - aligned_vector).tolist()
                }
        
        return aligned

