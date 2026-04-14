"""
BVH文件转换器
将MediaPipe输出的3D关键点数据转换为BVH的骨骼局部坐标系
"""

import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path


class BVHConverter:
    """BVH文件转换器"""
    
    def __init__(self):
        """初始化BVH转换器"""
        pass
    
    def convert_mediapipe_to_bvh(self, 
                                 mediapipe_data: List[Dict],
                                 output_path: str,
                                 frame_rate: float = 30.0):
        """
        将MediaPipe手部关键点数据转换为BVH文件
        
        Args:
            mediapipe_data: MediaPipe检测结果列表（每帧一个）
            output_path: 输出BVH文件路径
            frame_rate: 帧率
        """
        # BVH文件结构
        # HIERARCHY部分：定义骨骼层级
        # MOTION部分：定义动作数据
        
        bvh_content = []
        
        # 写入HIERARCHY部分
        bvh_content.append("HIERARCHY")
        bvh_content.append("ROOT Wrist")
        bvh_content.append("{")
        bvh_content.append("\tOFFSET 0.00 0.00 0.00")
        bvh_content.append("\tCHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")
        
        # 定义手部骨骼层级（简化版，基于21个关键点）
        # 这里需要根据实际需求定义骨骼层级
        bvh_content.append("\tJOINT Thumb_Base")
        bvh_content.append("\t{")
        bvh_content.append("\t\tOFFSET 0.00 0.00 0.00")
        bvh_content.append("\t\tCHANNELS 3 Zrotation Xrotation Yrotation")
        bvh_content.append("\t\tEnd Site")
        bvh_content.append("\t\t{")
        bvh_content.append("\t\t\tOFFSET 0.00 0.00 0.00")
        bvh_content.append("\t\t}")
        bvh_content.append("\t}")
        
        # 添加其他手指骨骼...
        # （简化实现，实际需要完整的21个关键点映射）
        
        bvh_content.append("}")
        
        # 写入MOTION部分
        bvh_content.append("MOTION")
        bvh_content.append(f"Frames: {len(mediapipe_data)}")
        bvh_content.append(f"Frame Time: {1.0/frame_rate:.6f}")
        
        # 写入每一帧的数据
        for frame_data in mediapipe_data:
            if frame_data:
                # 使用第一只手的数据
                hand = frame_data[0]
                landmarks_3d = hand['landmarks_3d']
                
                # 计算根节点位置（手腕）
                wrist_pos = landmarks_3d[0]
                
                # 计算旋转（简化处理）
                # 实际需要根据骨骼层级计算旋转角度
                rotation = self._calculate_rotation(landmarks_3d)
                
                # 写入帧数据
                frame_line = f"{wrist_pos['x']:.6f} {wrist_pos['y']:.6f} {wrist_pos['z']:.6f} "
                frame_line += f"{rotation[2]:.6f} {rotation[0]:.6f} {rotation[1]:.6f}"
                bvh_content.append(frame_line)
            else:
                # 无检测结果，使用默认值
                bvh_content.append("0.00 0.00 0.00 0.00 0.00 0.00")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bvh_content))
    
    def _calculate_rotation(self, landmarks_3d: List[Dict]) -> Tuple[float, float, float]:
        """
        根据关键点计算旋转角度（简化实现）
        
        Args:
            landmarks_3d: 3D关键点列表
            
        Returns:
            旋转角度 (x, y, z)
        """
        # 简化实现：使用手腕和手指方向计算旋转
        if len(landmarks_3d) < 5:
            return (0.0, 0.0, 0.0)
        
        wrist = np.array([landmarks_3d[0]['x'], landmarks_3d[0]['y'], landmarks_3d[0]['z']])
        middle_finger_mcp = np.array([
            landmarks_3d[9]['x'], 
            landmarks_3d[9]['y'], 
            landmarks_3d[9]['z']
        ])
        
        # 计算方向向量
        direction = middle_finger_mcp - wrist
        direction = direction / (np.linalg.norm(direction) + 1e-6)
        
        # 转换为欧拉角（简化）
        # 实际需要更复杂的计算
        y_rotation = np.arctan2(direction[0], direction[2])
        x_rotation = np.arcsin(-direction[1])
        z_rotation = 0.0
        
        return (
            np.degrees(x_rotation),
            np.degrees(y_rotation),
            np.degrees(z_rotation)
        )
    
    def read_bvh(self, bvh_path: str) -> Dict:
        """
        读取BVH文件
        
        Args:
            bvh_path: BVH文件路径
            
        Returns:
            BVH数据字典
        """
        with open(bvh_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        hierarchy = {}
        motion_data = []
        in_hierarchy = False
        in_motion = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line == "HIERARCHY":
                in_hierarchy = True
                continue
            elif line == "MOTION":
                in_hierarchy = False
                in_motion = True
                continue
            
            if in_motion:
                if line.startswith("Frames:"):
                    num_frames = int(line.split(":")[1].strip())
                elif line.startswith("Frame Time:"):
                    frame_time = float(line.split(":")[1].strip())
                elif not line.startswith("Frames:") and not line.startswith("Frame Time:"):
                    # 动作数据行
                    values = [float(v) for v in line.split()]
                    motion_data.append(values)
        
        return {
            'hierarchy': hierarchy,
            'motion_data': motion_data,
            'num_frames': len(motion_data),
            'frame_time': frame_time if 'frame_time' in locals() else 0.033
        }








