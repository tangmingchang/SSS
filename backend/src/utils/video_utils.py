"""
视频处理工具函数
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple


def extract_frames(video_path: str, 
                  output_dir: Optional[str] = None,
                  max_frames: Optional[int] = None) -> List[np.ndarray]:
    """
    从视频中提取帧
    
    Args:
        video_path: 视频路径
        output_dir: 输出目录（可选，如果提供则保存帧）
        max_frames: 最大帧数
        
    Returns:
        帧列表
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0
    
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frames.append(frame)
        frame_count += 1
        
        if output_dir:
            cv2.imwrite(str(Path(output_dir) / f"frame_{frame_count:06d}.jpg"), frame)
        
        if max_frames and frame_count >= max_frames:
            break
    
    cap.release()
    return frames


def get_video_info(video_path: str) -> dict:
    """
    获取视频信息
    
    Args:
        video_path: 视频路径
        
    Returns:
        视频信息字典
    """
    cap = cv2.VideoCapture(video_path)
    
    info = {
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
    }
    
    cap.release()
    return info


def create_video_from_frames(frames: List[np.ndarray],
                           output_path: str,
                           fps: float = 8.0,
                           codec: str = 'mp4v') -> str:
    """
    从帧列表创建视频
    
    Args:
        frames: 帧列表
        output_path: 输出路径
        fps: 帧率
        codec: 编解码器
        
    Returns:
        输出路径
    """
    if not frames:
        raise ValueError("帧列表为空")
    
    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        out.write(frame)
    
    out.release()
    return output_path


def resize_video(input_path: str,
                output_path: str,
                size: Tuple[int, int],
                fps: Optional[float] = None) -> str:
    """
    调整视频大小
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        size: 目标尺寸 (width, height)
        fps: 目标帧率（可选）
        
    Returns:
        输出路径
    """
    cap = cv2.VideoCapture(input_path)
    
    if fps is None:
        fps = cap.get(cv2.CAP_PROP_FPS)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, size)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        resized = cv2.resize(frame, size)
        out.write(resized)
    
    cap.release()
    out.release()
    return output_path

