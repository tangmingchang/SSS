"""
可视化工具函数
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Line2D


def visualize_keypoints(image: np.ndarray,
                       keypoints: Dict[str, Tuple[float, float]],
                       connections: Optional[List[Tuple[str, str]]] = None) -> np.ndarray:
    """
    可视化关键点
    
    Args:
        image: 输入图像
        keypoints: 关键点字典
        connections: 连接关系列表
        
    Returns:
        可视化后的图像
    """
    vis_image = image.copy()
    
    # 默认连接关系（COCO格式）
    if connections is None:
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
    
    # 绘制连接线
    for start_name, end_name in connections:
        if start_name in keypoints and end_name in keypoints:
            start = keypoints[start_name]
            end = keypoints[end_name]
            cv2.line(vis_image,
                    (int(start[0]), int(start[1])),
                    (int(end[0]), int(end[1])),
                    (0, 255, 0), 2)
    
    # 绘制关键点
    for name, (x, y) in keypoints.items():
        cv2.circle(vis_image, (int(x), int(y)), 5, (0, 0, 255), -1)
        cv2.putText(vis_image, name, (int(x) + 10, int(y)),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    return vis_image


def visualize_layers(layers: Dict[str, np.ndarray],
                    canvas_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    可视化图层结构
    
    Args:
        layers: 图层字典
        canvas_size: 画布大小
        
    Returns:
        可视化图像
    """
    if not layers:
        return np.zeros((512, 512, 3), dtype=np.uint8)
    
    # 创建网格布局
    num_layers = len(layers)
    cols = int(np.ceil(np.sqrt(num_layers)))
    rows = int(np.ceil(num_layers / cols))
    
    if canvas_size is None:
        # 使用第一个图层的大小
        first_layer = list(layers.values())[0]
        layer_h, layer_w = first_layer.shape[:2]
        canvas_w = layer_w * cols
        canvas_h = layer_h * rows
    else:
        canvas_w, canvas_h = canvas_size
    
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
    
    idx = 0
    for layer_name, layer_img in layers.items():
        row = idx // cols
        col = idx % cols
        
        # 转换为RGB
        if layer_img.shape[2] == 4:
            # RGBA转RGB
            alpha = layer_img[:, :, 3:4] / 255.0
            rgb = layer_img[:, :, :3]
            layer_rgb = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
        else:
            layer_rgb = layer_img[:, :, :3]
        
        # 调整大小以适应网格
        layer_h, layer_w = layer_rgb.shape[:2]
        cell_w = canvas_w // cols
        cell_h = canvas_h // rows
        
        resized = cv2.resize(layer_rgb, (cell_w, cell_h))
        
        # 放置到画布
        y_start = row * cell_h
        x_start = col * cell_w
        canvas[y_start:y_start+cell_h, x_start:x_start+cell_w] = resized
        
        # 添加标签
        cv2.putText(canvas, layer_name,
                   (x_start + 10, y_start + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        idx += 1
    
    return canvas


def create_comparison_image(images: List[np.ndarray],
                           labels: Optional[List[str]] = None) -> np.ndarray:
    """
    创建对比图像
    
    Args:
        images: 图像列表
        labels: 标签列表（可选）
        
    Returns:
        对比图像
    """
    num_images = len(images)
    if num_images == 0:
        return np.zeros((512, 512, 3), dtype=np.uint8)
    
    # 统一图像大小
    h, w = images[0].shape[:2]
    resized_images = []
    for img in images:
        if img.shape[:2] != (h, w):
            resized = cv2.resize(img, (w, h))
        else:
            resized = img
        resized_images.append(resized)
    
    # 创建水平拼接
    comparison = np.hstack(resized_images)
    
    # 添加标签
    if labels:
        for i, label in enumerate(labels):
            x = i * w + 10
            cv2.putText(comparison, label, (x, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return comparison


def save_animation_preview(frames: List[np.ndarray],
                          output_path: str,
                          grid_size: Tuple[int, int] = (4, 4)) -> str:
    """
    保存动画预览（网格形式）
    
    Args:
        frames: 帧列表
        output_path: 输出路径
        grid_size: 网格大小 (rows, cols)
        
    Returns:
        输出路径
    """
    rows, cols = grid_size
    num_frames = min(len(frames), rows * cols)
    
    if num_frames == 0:
        return output_path
    
    h, w = frames[0].shape[:2]
    preview = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)
    
    for i in range(num_frames):
        row = i // cols
        col = i % cols
        
        frame = frames[i]
        if frame.shape[2] == 4:
            # RGBA转RGB
            alpha = frame[:, :, 3:4] / 255.0
            rgb = frame[:, :, :3]
            frame_rgb = (rgb * alpha + (1 - alpha) * 255).astype(np.uint8)
        else:
            frame_rgb = frame[:, :, :3]
        
        y_start = row * h
        x_start = col * w
        preview[y_start:y_start+h, x_start:x_start+w] = frame_rgb
    
    cv2.imwrite(output_path, preview)
    return output_path








