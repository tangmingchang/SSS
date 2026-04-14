"""
反向动力学(IK)算法模块
约束关节运动范围，确保生成动作符合皮影操纵的生物力学规律
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional


class InverseKinematicsSolver:
    """反向动力学求解器"""
    
    def __init__(self, 
                 joint_limits: Optional[Dict[str, Tuple[float, float]]] = None,
                 chain_length: int = 3):
        """
        初始化IK求解器
        
        Args:
            joint_limits: 关节角度限制字典，格式为 {joint_name: (min_angle, max_angle)}
            chain_length: 骨骼链长度
        """
        self.joint_limits = joint_limits or self._get_default_limits()
        self.chain_length = chain_length
    
    def _get_default_limits(self) -> Dict[str, Tuple[float, float]]:
        """获取默认关节限制（基于皮影操纵特点）"""
        return {
            'shoulder': (-90, 90),      # 肩部：-90到90度
            'elbow': (0, 160),          # 肘部：0到160度
            'wrist': (-45, 45),         # 手腕：-45到45度
            'hip': (-45, 45),           # 髋部：-45到45度
            'knee': (0, 160),           # 膝盖：0到160度
            'ankle': (-30, 30),         # 脚踝：-30到30度
            'neck': (-30, 30),          # 颈部：-30到30度
            'head': (-20, 20),          # 头部：-20到20度
        }
    
    def solve_ik(self,
                 target_position: np.ndarray,
                 initial_joint_angles: np.ndarray,
                 bone_lengths: np.ndarray,
                 max_iterations: int = 50,
                 tolerance: float = 0.01) -> Tuple[np.ndarray, bool]:
        """
        求解IK问题
        
        Args:
            target_position: 目标位置 [3]
            initial_joint_angles: 初始关节角度 [N]
            bone_lengths: 骨骼长度 [chain_length]
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
            
        Returns:
            (关节角度, 是否收敛)
        """
        joint_angles = initial_joint_angles.copy()
        
        for iteration in range(max_iterations):
            # 计算当前末端位置
            current_position = self._forward_kinematics(joint_angles, bone_lengths)
            
            # 计算误差
            error = target_position - current_position
            error_norm = np.linalg.norm(error)
            
            if error_norm < tolerance:
                return joint_angles, True
            
            # 计算雅可比矩阵
            jacobian = self._compute_jacobian(joint_angles, bone_lengths)
            
            # 使用伪逆求解
            jacobian_pinv = np.linalg.pinv(jacobian)
            delta_angles = jacobian_pinv @ error
            
            # 更新关节角度
            joint_angles += delta_angles
            
            # 应用关节限制
            joint_angles = self._apply_joint_limits(joint_angles)
        
        return joint_angles, False
    
    def _forward_kinematics(self, 
                          joint_angles: np.ndarray,
                          bone_lengths: np.ndarray) -> np.ndarray:
        """前向运动学：根据关节角度计算末端位置"""
        position = np.array([0.0, 0.0, 0.0])
        rotation = np.eye(3)
        
        for i, angle in enumerate(joint_angles):
            if i >= len(bone_lengths):
                break
            
            # 旋转矩阵（绕Z轴）
            cos_a = np.cos(np.radians(angle))
            sin_a = np.sin(np.radians(angle))
            rot_z = np.array([
                [cos_a, -sin_a, 0],
                [sin_a, cos_a, 0],
                [0, 0, 1]
            ])
            
            rotation = rotation @ rot_z
            
            # 沿Y轴移动（骨骼长度）
            bone_dir = rotation @ np.array([0, bone_lengths[i], 0])
            position += bone_dir
        
        return position
    
    def _compute_jacobian(self,
                         joint_angles: np.ndarray,
                         bone_lengths: np.ndarray) -> np.ndarray:
        """计算雅可比矩阵"""
        jacobian = np.zeros((3, len(joint_angles)))
        epsilon = 1e-6
        
        current_pos = self._forward_kinematics(joint_angles, bone_lengths)
        
        for i in range(len(joint_angles)):
            # 数值微分
            angles_perturbed = joint_angles.copy()
            angles_perturbed[i] += epsilon
            
            perturbed_pos = self._forward_kinematics(angles_perturbed, bone_lengths)
            
            jacobian[:, i] = (perturbed_pos - current_pos) / epsilon
        
        return jacobian
    
    def _apply_joint_limits(self, joint_angles: np.ndarray) -> np.ndarray:
        """应用关节角度限制"""
        limited_angles = joint_angles.copy()
        
        # 简化处理：假设前N个关节对应不同的限制
        limit_keys = list(self.joint_limits.keys())
        
        for i, angle in enumerate(limited_angles):
            if i < len(limit_keys):
                joint_name = limit_keys[i]
                min_angle, max_angle = self.joint_limits[joint_name]
                limited_angles[i] = np.clip(angle, min_angle, max_angle)
        
        return limited_angles


class IKConstraintLayer(nn.Module):
    """IK约束层，用于神经网络中"""
    
    def __init__(self, 
                 joint_limits: Optional[Dict[str, Tuple[float, float]]] = None,
                 constraint_weight: float = 1.0):
        """
        初始化IK约束层
        
        Args:
            joint_limits: 关节限制
            constraint_weight: 约束权重
        """
        super().__init__()
        self.ik_solver = InverseKinematicsSolver(joint_limits)
        self.constraint_weight = constraint_weight
    
    def forward(self, 
               predicted_angles: torch.Tensor,
               target_positions: torch.Tensor,
               bone_lengths: torch.Tensor) -> torch.Tensor:
        """
        应用IK约束
        
        Args:
            predicted_angles: 预测的关节角度 [B, T, N]
            target_positions: 目标位置 [B, T, 3]
            bone_lengths: 骨骼长度 [B, chain_length]
            
        Returns:
            约束后的关节角度 [B, T, N]
        """
        batch_size, seq_len, num_joints = predicted_angles.shape
        constrained_angles = []
        
        for b in range(batch_size):
            batch_angles = []
            bone_lens = bone_lengths[b].cpu().numpy()
            
            for t in range(seq_len):
                angles = predicted_angles[b, t].cpu().numpy()
                target_pos = target_positions[b, t].cpu().numpy()
                
                # 求解IK
                constrained, converged = self.ik_solver.solve_ik(
                    target_pos,
                    angles,
                    bone_lens
                )
                
                batch_angles.append(constrained)
            
            constrained_angles.append(batch_angles)
        
        return torch.tensor(constrained_angles, device=predicted_angles.device).float()








