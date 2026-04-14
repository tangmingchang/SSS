"""
图层合成器 - 负责将多个图层合成为完整的角色图像
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from .layer_loader import LayerLoader


class LayerComposer:
    """图层合成器"""
    
    def __init__(self, layer_loader: LayerLoader):
        """
        初始化图层合成器
        
        Args:
            layer_loader: 图层加载器实例
        """
        self.layer_loader = layer_loader
        self.layer_hierarchy = layer_loader.get_layer_hierarchy()
    
    def compose(self, layers: Dict[str, np.ndarray], 
                transformations: Optional[Dict[str, Dict]] = None,
                canvas_size: Optional[Tuple[int, int]] = None,
                max_canvas_size: Optional[Tuple[int, int]] = (1920, 1080)) -> np.ndarray:
        """
        合成图层为完整图像
        
        Args:
            layers: 图层字典
            transformations: 每个图层的变换参数（旋转、缩放、平移等）
            canvas_size: 固定画布尺寸 (宽, 高)，若提供则直接使用，避免超大画布导致内存溢出
            max_canvas_size: 画布最大尺寸限制，自动计算时生效
            
        Returns:
            合成后的图像（RGBA格式）
        """
        if transformations is None:
            transformations = {}
        
        # 按照层级顺序排序图层
        sorted_layers = sorted(
            self.layer_hierarchy,
            key=lambda x: x['order']
        )
        
        # 确定画布大小：优先使用传入的固定尺寸，否则计算并限制最大尺寸
        if canvas_size is not None:
            canvas_size = (int(canvas_size[0]), int(canvas_size[1]))
        else:
            computed = self._calculate_canvas_size(layers, transformations)
            max_w, max_h = max_canvas_size or (1920, 1080)
            canvas_size = (
                min(computed[0], max_w),
                min(computed[1], max_h)
            )
        canvas = np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.uint8)
        
        # 按顺序合成图层
        for layer_info in sorted_layers:
            layer_name = layer_info['name']
            if layer_name in layers:
                layer_img = layers[layer_name]
                transform = transformations.get(layer_name, {})
                
                # 应用变换
                transformed_layer = self._apply_transform(layer_img, transform, canvas_size)
                
                # 合成到画布上
                canvas = self._blend_layer(canvas, transformed_layer)
        
        return canvas
    
    def _calculate_canvas_size(self, layers: Dict[str, np.ndarray],
                              transformations: Dict[str, Dict]) -> Tuple[int, int]:
        """计算画布大小"""
        max_width, max_height = 512, 768  # 默认大小
        
        for layer_name, layer_img in layers.items():
            if len(layer_img.shape) < 2:
                continue
            h, w = layer_img.shape[:2]
            transform = transformations.get(layer_name, {})
            
            # 考虑旋转和缩放
            scale = transform.get('scale', 1.0)
            angle = transform.get('rotation', 0.0)
            
            if abs(angle) > 0:
                rad = np.radians(angle)
                cos_a, sin_a = abs(np.cos(rad)), abs(np.sin(rad))
                new_w = int((w * cos_a + h * sin_a) * scale)
                new_h = int((w * sin_a + h * cos_a) * scale)
            else:
                new_w = int(w * scale)
                new_h = int(h * scale)
            
            max_width = max(max_width, new_w)
            max_height = max(max_height, new_h)
        
        return max_width, max_height
    
    def _apply_transform(self, img: np.ndarray, transform: Dict,
                         canvas_size: Tuple[int, int]) -> np.ndarray:
        """应用变换到图层"""
        h, w = img.shape[:2]
        
        # 获取变换参数
        rotation = transform.get('rotation', 0.0)
        scale = transform.get('scale', 1.0)
        translation = transform.get('translation', (canvas_size[0] // 2, canvas_size[1] // 2))
        
        # 确保图像有4个通道
        if img.shape[2] == 3:
            alpha = np.ones((h, w, 1), dtype=np.uint8) * 255
            img = np.concatenate([img, alpha], axis=2)
        
        # 创建变换矩阵
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, rotation, scale)
        M[0, 2] += translation[0] - w // 2
        M[1, 2] += translation[1] - h // 2
        
        # 应用变换
        transformed = cv2.warpAffine(
            img, M, (canvas_size[0], canvas_size[1]),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT
        )
        
        return transformed
    
    def _blend_layer(self, canvas: np.ndarray, layer: np.ndarray) -> np.ndarray:
        """将图层混合到画布上（支持透明度）"""
        # 确保尺寸匹配
        if canvas.shape[:2] != layer.shape[:2]:
            # 调整图层尺寸以匹配画布
            layer = cv2.resize(layer, (canvas.shape[1], canvas.shape[0]), interpolation=cv2.INTER_LINEAR)
        
        if layer.shape[2] == 4:
            # 有alpha通道
            alpha = layer[:, :, 3:4] / 255.0
            rgb = layer[:, :, :3]
            
            canvas_rgb = canvas[:, :, :3]
            canvas_alpha = canvas[:, :, 3:4] / 255.0
            
            # Alpha混合（使用 float32 降低内存占用，避免 367MB+ 的 float64 分配）
            new_alpha = alpha.astype(np.float32) + canvas_alpha.astype(np.float32) * (1 - alpha.astype(np.float32))
            new_rgb = (
                rgb.astype(np.float32) * alpha.astype(np.float32)
                + canvas_rgb.astype(np.float32) * canvas_alpha.astype(np.float32) * (1 - alpha.astype(np.float32))
            ) / np.maximum(new_alpha, 1e-6)
            
            result = np.zeros_like(canvas)
            result[:, :, :3] = np.clip(new_rgb, 0, 255).astype(np.uint8)
            result[:, :, 3] = (new_alpha.squeeze(2) * 255).astype(np.uint8)  # 修复：squeeze去掉维度
            
            return result
        else:
            # 无alpha通道，直接覆盖
            if layer.shape[2] == 3:
                # 添加alpha通道
                alpha = np.ones((layer.shape[0], layer.shape[1], 1), dtype=np.uint8) * 255
                layer = np.concatenate([layer, alpha], axis=2)
            mask = layer[:, :, 3] > 0
            canvas[mask] = layer[mask]
            return canvas
    
    def get_layer_positions(self, keypoints: Dict[str, Tuple[float, float]],
                           canvas_size: Tuple[int, int]) -> Dict[str, Dict]:
        """
        根据关键点计算各图层的位置和变换
        
        Args:
            keypoints: 关键点字典，键为关键点名称，值为(x, y)坐标
            canvas_size: 画布大小
            
        Returns:
            每个图层的变换参数字典
        """
        transformations = {}
        
        for layer_info in self.layer_hierarchy:
            layer_name = layer_info['name']
            parent_name = layer_info.get('parent')
            joint_name = layer_info.get('joint')
            
            if joint_name and joint_name in keypoints:
                joint_pos = keypoints[joint_name]
                
                # 计算相对于父图层的变换
                if parent_name and parent_name in transformations:
                    parent_transform = transformations[parent_name]
                    # 这里需要根据父子关系计算相对变换
                    # 简化处理：直接使用关键点位置
                    pass
                
                # 计算旋转角度（如果有父关节）
                rotation = 0.0
                if parent_name and parent_name in keypoints:
                    parent_pos = keypoints[parent_name]
                    dx = joint_pos[0] - parent_pos[0]
                    dy = joint_pos[1] - parent_pos[1]
                    rotation = np.degrees(np.arctan2(dy, dx))
                
                transformations[layer_name] = {
                    'translation': joint_pos,
                    'rotation': rotation,
                    'scale': 1.0
                }
        
        return transformations

