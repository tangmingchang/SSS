"""
24关节BVH转换器（已废弃，保留作为后备）

注意: 此文件已废弃，保留仅作为后备方案
新方案请使用: backend/src/motion_capture/vibe_integration.py 中的 SMPL2BVHConverter

原因: 使用 MediaPipe 2D 关键点转换的 BVH 质量较差，已被 VIBE + smpl2bvh 方案替代
"""

# ============================================================================
# 已废弃 - 保留作为后备方案
# 新代码请使用: vibe_integration.SMPL2BVHConverter
# ============================================================================
"""
24关节BVH转换器
将24关节姿态数据转换为完整的BVH格式
"""

import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path


class BVH24JointsConverter:
    """24关节BVH转换器"""
    
    # 骨骼层级定义（24关节）
    BONE_HIERARCHY = {
        "Root": {
            "offset": (0, 0, 0),
            "channels": ["Xposition", "Yposition", "Zposition", "Zrotation", "Xrotation", "Yrotation"],
            "children": ["Hips"]
        },
        "Hips": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["Spine", "LeftHip", "RightHip"]
        },
        "Spine": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["Spine1"]
        },
        "Spine1": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["Neck"]
        },
        "Neck": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["Head"]
        },
        "Head": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": []
        },
        "LeftHip": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["LeftKnee"]
        },
        "LeftKnee": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["LeftAnkle"]
        },
        "LeftAnkle": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": []
        },
        "RightHip": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["RightKnee"]
        },
        "RightKnee": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["RightAnkle"]
        },
        "RightAnkle": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": []
        },
        "LeftShoulder": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["LeftArm"]
        },
        "LeftArm": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["LeftForeArm"]
        },
        "LeftForeArm": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["LeftHand"]
        },
        "LeftHand": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": []
        },
        "RightShoulder": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["RightArm"]
        },
        "RightArm": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["RightForeArm"]
        },
        "RightForeArm": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": ["RightHand"]
        },
        "RightHand": {
            "offset": (0, 0, 0),
            "channels": ["Zrotation", "Xrotation", "Yrotation"],
            "children": []
        }
    }
    
    # 关节到骨骼的映射
    JOINT_TO_BONE = {
        "MidHip": "Hips",
        "LHip": "LeftHip",
        "LKnee": "LeftKnee",
        "LAnkle": "LeftAnkle",
        "RHip": "RightHip",
        "RKnee": "RightKnee",
        "RAnkle": "RightAnkle",
        "Neck": "Neck",
        "Nose": "Head",
        "LShoulder": "LeftShoulder",
        "LElbow": "LeftArm",
        "LWrist": "LeftForeArm",
        "RShoulder": "RightShoulder",
        "RElbow": "RightArm",
        "RWrist": "RightForeArm",
    }
    
    def __init__(self):
        """初始化BVH转换器"""
        self.bone_order = self._get_bone_order()
    
    def _get_bone_order(self) -> List[str]:
        """获取骨骼顺序（按层级遍历）"""
        order = []
        
        def traverse(bone_name: str):
            order.append(bone_name)
            if bone_name in self.BONE_HIERARCHY:
                for child in self.BONE_HIERARCHY[bone_name].get("children", []):
                    traverse(child)
        
        traverse("Root")
        return order
    
    def convert_24_joints_to_bvh(self,
                                 joints_sequence: List[Dict[str, Tuple[float, float, float]]],
                                 output_path: str,
                                 frame_rate: float = 30.0):
        """
        将24关节序列转换为BVH文件
        
        Args:
            joints_sequence: 24关节序列（每帧一个字典）
            output_path: 输出BVH文件路径
            frame_rate: 帧率
        """
        bvh_content = []
        
        # 1. 写入HIERARCHY部分
        bvh_content.append("HIERARCHY")
        self._write_hierarchy(bvh_content, "Root", indent=0)
        
        # 2. 写入MOTION部分
        bvh_content.append("MOTION")
        bvh_content.append(f"Frames: {len(joints_sequence)}")
        bvh_content.append(f"Frame Time: {1.0/frame_rate:.6f}")
        
        # 3. 计算每帧的骨骼数据
        for frame_joints in joints_sequence:
            frame_data = self._calculate_frame_data(frame_joints)
            bvh_content.append(frame_data)
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bvh_content))
    
    def _write_hierarchy(self, content: List[str], bone_name: str, indent: int = 0):
        """递归写入骨骼层级"""
        indent_str = "\t" * indent
        
        if bone_name == "Root":
            content.append(f"{indent_str}ROOT {bone_name}")
        else:
            content.append(f"{indent_str}JOINT {bone_name}")
        
        content.append(f"{indent_str}{{")
        
        bone_info = self.BONE_HIERARCHY[bone_name]
        offset = bone_info["offset"]
        channels = bone_info["channels"]
        
        content.append(f"{indent_str}\tOFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}")
        content.append(f"{indent_str}\tCHANNELS {len(channels)} {' '.join(channels)}")
        
        children = bone_info.get("children", [])
        if not children:
            # End Site
            content.append(f"{indent_str}\tEnd Site")
            content.append(f"{indent_str}\t{{")
            content.append(f"{indent_str}\t\tOFFSET 0.00 0.00 0.00")
            content.append(f"{indent_str}\t}}")
        else:
            for child in children:
                self._write_hierarchy(content, child, indent + 1)
        
        content.append(f"{indent_str}}}")
    
    def _calculate_frame_data(self, joints: Dict[str, Tuple[float, float, float]]) -> str:
        """
        计算单帧的BVH数据
        
        Args:
            joints: 24关节字典
            
        Returns:
            BVH数据行（空格分隔的数值）
        """
        frame_values = []
        
        # 遍历所有骨骼，计算旋转和位置
        for bone_name in self.bone_order:
            if bone_name == "Root":
                # Root节点：位置 + 旋转
                if "MidHip" in joints:
                    hip = joints["MidHip"]
                    frame_values.extend([f"{hip[0]:.6f}", f"{hip[1]:.6f}", f"{hip[2]:.6f}"])
                else:
                    frame_values.extend(["0.000000", "0.000000", "0.000000"])
                
                # Root旋转
                rotation = self._calculate_bone_rotation(bone_name, joints)
                frame_values.extend([f"{rotation[2]:.6f}", f"{rotation[0]:.6f}", f"{rotation[1]:.6f}"])
            else:
                # 其他骨骼：只有旋转
                rotation = self._calculate_bone_rotation(bone_name, joints)
                frame_values.extend([f"{rotation[2]:.6f}", f"{rotation[0]:.6f}", f"{rotation[1]:.6f}"])
        
        return " ".join(frame_values)
    
    def _calculate_bone_rotation(self,
                                bone_name: str,
                                joints: Dict[str, Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """
        计算骨骼旋转角度
        
        Args:
            bone_name: 骨骼名称
            joints: 关节字典
            
        Returns:
            旋转角度 (x, y, z) 单位：度
        """
        # 根据骨骼名称找到对应的关节
        joint_mapping = {
            "Hips": ("MidHip", None),
            "LeftHip": ("LHip", "LKnee"),
            "LeftKnee": ("LKnee", "LAnkle"),
            "LeftAnkle": ("LAnkle", None),
            "RightHip": ("RHip", "RKnee"),
            "RightKnee": ("RKnee", "RAnkle"),
            "RightAnkle": ("RAnkle", None),
            "Spine": ("MidHip", "Neck"),
            "Spine1": ("MidHip", "Neck"),
            "Neck": ("Neck", "Nose"),
            "Head": ("Neck", "Nose"),
            "LeftShoulder": ("LShoulder", "LElbow"),
            "LeftArm": ("LElbow", "LWrist"),
            "LeftForeArm": ("LWrist", None),
            "LeftHand": ("LWrist", None),
            "RightShoulder": ("RShoulder", "RElbow"),
            "RightArm": ("RElbow", "RWrist"),
            "RightForeArm": ("RWrist", None),
            "RightHand": ("RWrist", None),
        }
        
        if bone_name not in joint_mapping:
            return (0.0, 0.0, 0.0)
        
        start_joint, end_joint = joint_mapping[bone_name]
        
        if start_joint not in joints:
            return (0.0, 0.0, 0.0)
        
        start_pos = np.array(joints[start_joint])
        
        if end_joint and end_joint in joints:
            # 有子关节，计算方向
            end_pos = np.array(joints[end_joint])
            direction = end_pos - start_pos
            direction = direction / (np.linalg.norm(direction) + 1e-6)
            
            # 转换为欧拉角
            y_rotation = np.arctan2(direction[0], direction[2])
            x_rotation = np.arcsin(-direction[1])
            z_rotation = 0.0
            
            return (
                np.degrees(x_rotation),
                np.degrees(y_rotation),
                np.degrees(z_rotation)
            )
        else:
            # 没有子关节，使用默认旋转
            return (0.0, 0.0, 0.0)








