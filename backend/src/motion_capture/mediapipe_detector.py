"""
MediaPipe手部关键点检测器
实现21个手部关节的2D/3D坐标提取
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("警告: MediaPipe未安装，请运行: pip install mediapipe")


class MediaPipeHandDetector:
    """MediaPipe手部关键点检测器"""
    
    # MediaPipe手部21个关键点定义
    HAND_LANDMARKS = [
        "WRIST",           # 0: 手腕
        "THUMB_CMC",       # 1: 拇指CMC
        "THUMB_MCP",       # 2: 拇指MCP
        "THUMB_IP",        # 3: 拇指IP
        "THUMB_TIP",       # 4: 拇指尖
        "INDEX_FINGER_MCP", # 5: 食指MCP
        "INDEX_FINGER_PIP", # 6: 食指PIP
        "INDEX_FINGER_DIP", # 7: 食指DIP
        "INDEX_FINGER_TIP", # 8: 食指尖
        "MIDDLE_FINGER_MCP", # 9: 中指MCP
        "MIDDLE_FINGER_PIP", # 10: 中指PIP
        "MIDDLE_FINGER_DIP", # 11: 中指DIP
        "MIDDLE_FINGER_TIP", # 12: 中指尖
        "RING_FINGER_MCP", # 13: 无名指MCP
        "RING_FINGER_PIP", # 14: 无名指PIP
        "RING_FINGER_DIP", # 15: 无名指DIP
        "RING_FINGER_TIP", # 16: 无名指尖
        "PINKY_MCP",      # 17: 小指MCP
        "PINKY_PIP",      # 18: 小指PIP
        "PINKY_DIP",      # 19: 小指DIP
        "PINKY_TIP"       # 20: 小指尖
    ]
    
    def __init__(self, 
                 static_image_mode: bool = False,
                 max_num_hands: int = 2,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """
        初始化MediaPipe手部检测器
        
        Args:
            static_image_mode: 静态图像模式
            max_num_hands: 最大手部数量
            min_detection_confidence: 最小检测置信度
            min_tracking_confidence: 最小跟踪置信度
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe未安装，请运行: pip install mediapipe")
        
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
    
    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        检测图像中的手部关键点
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            手部关键点列表，每个元素包含：
            - landmarks_2d: 2D坐标列表
            - landmarks_3d: 3D坐标列表
            - handedness: 左右手信息
        """
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 检测
        results = self.hands.process(rgb_image)
        
        hands_data = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                # 提取2D坐标（归一化）
                landmarks_2d = []
                h, w = image.shape[:2]
                
                for landmark in hand_landmarks.landmark:
                    landmarks_2d.append({
                        'x': landmark.x * w,
                        'y': landmark.y * h,
                        'z': landmark.z  # 相对深度
                    })
                
                # 提取3D坐标（MediaPipe提供的是相对3D坐标）
                landmarks_3d = []
                for landmark in hand_landmarks.landmark:
                    landmarks_3d.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                
                hands_data.append({
                    'landmarks_2d': landmarks_2d,
                    'landmarks_3d': landmarks_3d,
                    'handedness': handedness.classification[0].label,  # Left or Right
                    'confidence': handedness.classification[0].score
                })
        
        return hands_data
    
    def detect_video(self, video_path: str) -> List[List[Dict]]:
        """
        检测视频中每一帧的手部关键点
        
        Args:
            video_path: 视频路径
            
        Returns:
            每一帧的手部关键点列表
        """
        if not hasattr(cv2, 'VideoCapture'):
            raise AttributeError("cv2.VideoCapture 不可用，请检查 OpenCV 安装")
        cap = cv2.VideoCapture(str(video_path))
        all_hands_data = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            hands_data = self.detect(frame)
            all_hands_data.append(hands_data)
        
        cap.release()
        return all_hands_data
    
    def visualize(self, image: np.ndarray, hands_data: List[Dict]) -> np.ndarray:
        """
        可视化手部关键点
        
        Args:
            image: 输入图像
            hands_data: 手部关键点数据
            
        Returns:
            可视化后的图像
        """
        vis_image = image.copy()
        rgb_image = cv2.cvtColor(vis_image, cv2.COLOR_BGR2RGB)
        
        # 创建临时结果对象用于绘制
        # 注意：这里需要重新处理图像以获取landmarks对象
        results = self.hands.process(rgb_image)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    vis_image,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
        
        return vis_image








