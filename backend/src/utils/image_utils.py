"""
图像处理工具函数
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional


def resize_image(image: np.ndarray, size: Tuple[int, int], 
                keep_aspect: bool = True) -> np.ndarray:
    """
    调整图像大小
    
    Args:
        image: 输入图像
        size: 目标尺寸 (width, height)
        keep_aspect: 是否保持宽高比
        
    Returns:
        调整后的图像
    """
    if keep_aspect:
        h, w = image.shape[:2]
        target_w, target_h = size
        
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # 填充到目标尺寸
        result = np.zeros((target_h, target_w, image.shape[2]), dtype=image.dtype)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return result
    else:
        return cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)


def normalize_image(image: np.ndarray) -> np.ndarray:
    """归一化图像到[0, 1]范围"""
    if image.dtype == np.uint8:
        return image.astype(np.float32) / 255.0
    return image


def denormalize_image(image: np.ndarray) -> np.ndarray:
    """反归一化图像到[0, 255]范围"""
    if image.max() <= 1.0:
        return (image * 255).astype(np.uint8)
    return image.astype(np.uint8)


def remove_background(image: np.ndarray, method: str = "threshold") -> np.ndarray:
    """
    移除背景
    
    Args:
        image: 输入图像
        method: 方法 ("threshold", "grabcut", "chromakey")
        
    Returns:
        带alpha通道的图像
    """
    if method == "threshold":
        # 简单的阈值方法
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        result = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
        result[:, :, :3] = image
        result[:, :, 3] = mask
        
        return result
    
    elif method == "chromakey":
        # 色度键方法（绿幕/蓝幕）
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # 这里需要根据实际背景颜色调整
        lower = np.array([40, 50, 50])
        upper = np.array([80, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.bitwise_not(mask)
        
        result = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
        result[:, :, :3] = image
        result[:, :, 3] = mask
        
        return result
    
    else:
        raise ValueError(f"不支持的方法: {method}")


def apply_color_adjustment(image: np.ndarray, 
                          brightness: float = 0.0,
                          contrast: float = 1.0,
                          saturation: float = 1.0) -> np.ndarray:
    """
    应用颜色调整
    
    Args:
        image: 输入图像
        brightness: 亮度调整 (-100 to 100)
        contrast: 对比度调整 (0.0 to 2.0)
        saturation: 饱和度调整 (0.0 to 2.0)
        
    Returns:
        调整后的图像
    """
    result = image.astype(np.float32)
    
    # 亮度调整
    result += brightness
    
    # 对比度调整
    result = (result - 128) * contrast + 128
    
    # 饱和度调整（转换为HSV）
    hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
    result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    
    return np.clip(result, 0, 255).astype(np.uint8)

