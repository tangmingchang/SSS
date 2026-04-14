"""
姿态检测器 - 基于DWPose/OpenPose的姿态检测
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional

# onnxruntime是可选的，如果没有安装则使用简化版本
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
    ort = None


class PoseDetector:
    """姿态检测器"""
    
    # COCO关键点定义
    COCO_KEYPOINTS = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    
    def __init__(self, model_path: str = None, detector_type: str = "dwpose"):
        """
        初始化姿态检测器
        
        Args:
            model_path: 模型路径
            detector_type: 检测器类型 ("dwpose" 或 "openpose")
        """
        self.detector_type = detector_type
        self.model_path = model_path
        
        if detector_type == "dwpose":
            self._init_dwpose(model_path)
        else:
            raise ValueError(f"不支持的检测器类型: {detector_type}")
    
    def _init_dwpose(self, model_path: str):
        """初始化DWPose模型"""
        self.detector = None
        self.use_simple_mode = not ONNXRUNTIME_AVAILABLE
        
        if model_path and ONNXRUNTIME_AVAILABLE:
            try:
                # 实际实现中应该加载ONNX模型
                # self.detector = ort.InferenceSession(model_path)
                pass
            except Exception as e:
                print(f"警告: 无法加载DWPose模型，使用简化模式: {e}")
                self.use_simple_mode = True
        else:
            if not ONNXRUNTIME_AVAILABLE:
                print("提示: onnxruntime未安装，使用简化姿态检测模式")
            self.use_simple_mode = True
    
    def detect(self, image: np.ndarray) -> Dict[str, Tuple[float, float]]:
        """
        检测图像中的姿态关键点
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            关键点字典，键为关键点名称，值为(x, y)坐标
        """
        if self.detector_type == "dwpose":
            return self._detect_dwpose(image)
        else:
            raise ValueError(f"不支持的检测器类型: {self.detector_type}")
    
    def _detect_dwpose(self, image: np.ndarray) -> Dict[str, Tuple[float, float]]:
        """
        使用DWPose检测姿态
        
        Args:
            image: 输入图像
            
        Returns:
            关键点字典
        """
        # 这里应该调用实际的DWPose模型
        # 由于没有实际模型，这里返回一个示例结构
        
        h, w = image.shape[:2]
        keypoints = {}
        
        # 示例：返回一些默认位置（实际应该从模型输出）
        # 这里提供一个框架，实际使用时需要替换为真实的检测结果
        keypoints["nose"] = (w * 0.5, h * 0.2)
        keypoints["left_eye"] = (w * 0.45, h * 0.18)
        keypoints["right_eye"] = (w * 0.55, h * 0.18)
        keypoints["left_shoulder"] = (w * 0.4, h * 0.4)
        keypoints["right_shoulder"] = (w * 0.6, h * 0.4)
        keypoints["left_elbow"] = (w * 0.3, h * 0.5)
        keypoints["right_elbow"] = (w * 0.7, h * 0.5)
        keypoints["left_wrist"] = (w * 0.25, h * 0.6)
        keypoints["right_wrist"] = (w * 0.75, h * 0.6)
        keypoints["left_hip"] = (w * 0.45, h * 0.65)
        keypoints["right_hip"] = (w * 0.55, h * 0.65)
        keypoints["left_knee"] = (w * 0.45, h * 0.8)
        keypoints["right_knee"] = (w * 0.55, h * 0.8)
        keypoints["left_ankle"] = (w * 0.45, h * 0.95)
        keypoints["right_ankle"] = (w * 0.55, h * 0.95)
        
        # 计算neck位置
        if "left_shoulder" in keypoints and "right_shoulder" in keypoints:
            ls = keypoints["left_shoulder"]
            rs = keypoints["right_shoulder"]
            keypoints["neck"] = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        
        return keypoints
    
    def detect_video(self, video_path: str) -> List[Dict[str, Tuple[float, float]]]:
        """
        检测视频中每一帧的姿态
        
        Args:
            video_path: 视频路径
            
        Returns:
            每一帧的关键点列表
        """
        cap = cv2.VideoCapture(video_path)
        keypoints_list = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            keypoints = self.detect(frame)
            keypoints_list.append(keypoints)
        
        cap.release()
        return keypoints_list
    
    def visualize_keypoints(self, image: np.ndarray, 
                          keypoints: Dict[str, Tuple[float, float]]) -> np.ndarray:
        """
        可视化关键点
        
        Args:
            image: 输入图像
            keypoints: 关键点字典
            
        Returns:
            可视化后的图像
        """
        vis_image = image.copy()
        
        # 绘制关键点
        for name, (x, y) in keypoints.items():
            cv2.circle(vis_image, (int(x), int(y)), 5, (0, 255, 0), -1)
            cv2.putText(vis_image, name, (int(x) + 10, int(y)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 绘制骨架连接
        connections = [
            ("nose", "left_eye"), ("nose", "right_eye"),
            ("left_eye", "left_ear"), ("right_eye", "right_ear"),
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
        ]
        
        for start_name, end_name in connections:
            if start_name in keypoints and end_name in keypoints:
                start = keypoints[start_name]
                end = keypoints[end_name]
                cv2.line(vis_image, 
                        (int(start[0]), int(start[1])),
                        (int(end[0]), int(end[1])),
                        (0, 255, 0), 2)
        
        return vis_image

