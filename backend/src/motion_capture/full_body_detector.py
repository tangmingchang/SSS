"""
全身姿态检测器 - 24关节检测（已废弃，保留作为后备）

注意: 此文件已废弃，保留仅作为后备方案
新方案请使用: backend/src/motion_capture/vibe_integration.py 中的 VIBEPipeline

原因: MediaPipe 只能提取 2D 关键点，准确度较低，已被 VIBE + smpl2bvh 方案替代
"""

# ============================================================================
# 已废弃 - 保留作为后备方案
# 新代码请使用: vibe_integration.VIBEPipeline
# ============================================================================
"""
全身姿态检测器 - 24关节检测
基于OpenPose BODY_25格式，提取24个主要关节
"""

import numpy as np
from typing import Dict, List, Tuple, Optional

# 延迟导入 cv2，避免可能的导入问题
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("警告: OpenCV 未正确安装")

from ..pose.pose_detector import PoseDetector


class FullBodyDetector:
    """24关节全身姿态检测器"""
    
    # 24关节定义（基于OpenPose BODY_25，去除背景）
    JOINT_NAMES = [
        "Nose",           # 0
        "Neck",           # 1 (计算得出)
        "RShoulder",      # 2
        "RElbow",         # 3
        "RWrist",         # 4
        "LShoulder",      # 5
        "LElbow",         # 6
        "LWrist",         # 7
        "MidHip",         # 8 (计算得出)
        "RHip",           # 9
        "RKnee",          # 10
        "RAnkle",         # 11
        "LHip",           # 12
        "LKnee",          # 13
        "LAnkle",         # 14
        "REye",           # 15
        "LEye",           # 16
        "REar",           # 17
        "LEar",           # 18
        "LBigToe",        # 19
        "LSmallToe",      # 20
        "LHeel",          # 21
        "RBigToe",        # 22
        "RSmallToe",      # 23
        "RHeel",          # 24
    ]
    
    # OpenPose BODY_25到24关节的映射
    OPENPOSE_TO_24 = {
        0: 0,   # Nose
        1: 1,   # Neck (计算)
        2: 2,   # RShoulder
        3: 3,   # RElbow
        4: 4,   # RWrist
        5: 5,   # LShoulder
        6: 6,   # LElbow
        7: 7,   # LWrist
        8: 8,   # MidHip (计算)
        9: 9,   # RHip
        10: 10, # RKnee
        11: 11, # RAnkle
        12: 12, # LHip
        13: 13, # LKnee
        14: 14, # LAnkle
        15: 15, # REye
        16: 16, # LEye
        17: 17, # REar
        18: 18, # LEar
        19: 19, # LBigToe
        20: 20, # LSmallToe
        21: 21, # LHeel
        22: 22, # RBigToe
        23: 23, # RSmallToe
        24: 24, # RHeel
    }
    
    def __init__(self, pose_detector: Optional[PoseDetector] = None):
        """
        初始化全身检测器
        
        Args:
            pose_detector: 姿态检测器（如果为None，则创建新的）
        """
        if pose_detector is None:
            self.pose_detector = PoseDetector()
        else:
            self.pose_detector = pose_detector
    
    def detect_24_joints(self, image: np.ndarray) -> Dict[str, Tuple[float, float, float]]:
        """
        检测24个关节
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            关节字典，键为关节名称，值为(x, y, confidence)或(x, y, z)
        """
        # 使用基础姿态检测器
        keypoints_2d = self.pose_detector.detect(image)
        
        # 转换为24关节格式
        joints_24 = {}
        
        # 映射COCO关键点到24关节
        coco_to_24 = {
            "nose": "Nose",
            "left_eye": "LEye",
            "right_eye": "REye",
            "left_ear": "LEar",
            "right_ear": "REar",
            "left_shoulder": "LShoulder",
            "right_shoulder": "RShoulder",
            "left_elbow": "LElbow",
            "right_elbow": "RElbow",
            "left_wrist": "LWrist",
            "right_wrist": "RWrist",
            "left_hip": "LHip",
            "right_hip": "RHip",
            "left_knee": "LKnee",
            "right_knee": "RKnee",
            "left_ankle": "LAnkle",
            "right_ankle": "RAnkle",
        }
        
        # 转换已知关键点
        for coco_name, joint_name in coco_to_24.items():
            if coco_name in keypoints_2d:
                x, y = keypoints_2d[coco_name]
                # 估算z坐标（深度，简化处理）
                z = self._estimate_depth(coco_name, keypoints_2d)
                joints_24[joint_name] = (x, y, z)
        
        # 计算Neck（左右肩的中点）
        if "LShoulder" in joints_24 and "RShoulder" in joints_24:
            ls = joints_24["LShoulder"]
            rs = joints_24["RShoulder"]
            joints_24["Neck"] = (
                (ls[0] + rs[0]) / 2,
                (ls[1] + rs[1]) / 2,
                (ls[2] + rs[2]) / 2
            )
        
        # 计算MidHip（左右髋的中点）
        if "LHip" in joints_24 and "RHip" in joints_24:
            lh = joints_24["LHip"]
            rh = joints_24["RHip"]
            joints_24["MidHip"] = (
                (lh[0] + rh[0]) / 2,
                (lh[1] + rh[1]) / 2,
                (lh[2] + rh[2]) / 2
            )
        
        # 估算脚部关键点（如果不存在）
        for side in ["L", "R"]:
            ankle_name = f"{side}Ankle"
            if ankle_name in joints_24:
                ankle = joints_24[ankle_name]
                # 估算脚趾和脚跟位置
                joints_24[f"{side}BigToe"] = (ankle[0], ankle[1] - 20, ankle[2])
                joints_24[f"{side}SmallToe"] = (ankle[0] + 10, ankle[1] - 20, ankle[2])
                joints_24[f"{side}Heel"] = (ankle[0], ankle[1] + 10, ankle[2])
        
        return joints_24
    
    def _estimate_depth(self, joint_name: str, keypoints: Dict) -> float:
        """
        估算关节深度（z坐标）
        
        Args:
            joint_name: 关节名称
            keypoints: 关键点字典
            
        Returns:
            估算的深度值
        """
        # 简化处理：根据关节类型估算深度
        depth_map = {
            "nose": 0.0,
            "left_eye": -0.05,
            "right_eye": -0.05,
            "left_ear": -0.1,
            "right_ear": -0.1,
            "left_shoulder": 0.0,
            "right_shoulder": 0.0,
            "left_elbow": 0.1,
            "right_elbow": 0.1,
            "left_wrist": 0.2,
            "right_wrist": 0.2,
            "left_hip": 0.0,
            "right_hip": 0.0,
            "left_knee": 0.1,
            "right_knee": 0.1,
            "left_ankle": 0.2,
            "right_ankle": 0.2,
        }
        
        return depth_map.get(joint_name, 0.0)
    
    def detect_video_24_joints(self, video_path: str) -> List[Dict[str, Tuple[float, float, float]]]:
        """
        检测视频中每一帧的24关节
        
        Args:
            video_path: 视频路径
            
        Returns:
            每一帧的24关节列表
        """
        if not HAS_CV2:
            raise ImportError("OpenCV 未正确安装，无法读取视频")
        
        # 确保 cv2.VideoCapture 可用
        if not hasattr(cv2, 'VideoCapture'):
            raise AttributeError("cv2.VideoCapture 不可用，请检查 OpenCV 安装")
        
        cap = cv2.VideoCapture(str(video_path))
        joints_list = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            joints = self.detect_24_joints(frame)
            joints_list.append(joints)
        
        cap.release()
        return joints_list








