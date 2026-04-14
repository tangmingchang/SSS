"""
图层加载器 - 负责加载和管理皮影角色的图层文件
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import yaml


class LayerLoader:
    """皮影图层加载器"""
    
    def __init__(self, layer_config_path: str = "configs/layer_config.yaml"):
        """
        初始化图层加载器
        
        Args:
            layer_config_path: 图层配置文件路径
        """
        with open(layer_config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.layer_hierarchy = self.config['layer_hierarchy']
        self.naming_patterns = self.config['naming_patterns']
        self.layer_anchors = self.config.get('layer_anchors', {})
        
    def load_character(self, character_dir: str) -> Dict[str, np.ndarray]:
        """
        加载角色的所有图层
        
        Args:
            character_dir: 角色目录路径
            
        Returns:
            图层字典，键为图层名称，值为图像数组
        """
        character_path = Path(character_dir).resolve()
        if not character_path.exists():
            raise ValueError(f"角色目录不存在: {character_dir}\n绝对路径: {character_path}")
        
        layers = {}
        # 使用 resolve() 确保路径正确
        layer_files = list(character_path.glob("*.png")) + list(character_path.glob("*.jpg"))
        
        if not layer_files:
            raise ValueError(f"角色目录中没有找到图层文件: {character_path}")
        
        # 首先尝试精确匹配命名模式
        for layer_info in self.layer_hierarchy:
            layer_name = layer_info['name']
            matched_file = self._find_layer_file(layer_files, layer_name)
            if matched_file:
                layers[layer_name] = self._load_image(matched_file)
                layer_files.remove(matched_file)
        
        # 处理剩余的图层文件（可能是"图层 1.png"这样的格式）
        remaining_layers = sorted(layer_files, key=lambda x: self._extract_layer_number(x))
        for i, layer_file in enumerate(remaining_layers):
            # 尝试根据顺序推断图层名称
            if i < len(self.layer_hierarchy):
                layer_name = self.layer_hierarchy[i]['name']
                if layer_name not in layers:
                    layers[layer_name] = self._load_image(layer_file)
        
        return layers
    
    def _find_layer_file(self, files: List[Path], layer_name: str) -> Optional[Path]:
        """根据图层名称查找对应的文件"""
        # 精确匹配
        for file in files:
            if file.stem == layer_name or file.stem.lower() == layer_name.lower():
                return file
        
        # 模式匹配
        for pattern_info in self.naming_patterns:
            pattern = pattern_info['pattern']
            if pattern_info['layer_name'] == layer_name:
                regex = re.compile(pattern, re.IGNORECASE)
                for file in files:
                    if regex.search(file.stem):
                        return file
        
        return None
    
    def _extract_layer_number(self, file_path: Path) -> int:
        """从文件名中提取图层编号"""
        match = re.search(r'(\d+)', file_path.stem)
        return int(match.group(1)) if match else 999
    
    def _load_image(self, file_path: Path) -> np.ndarray:
        """
        加载图像文件（支持中文路径）
        
        注意：OpenCV 的 cv2.imread() 在 Windows 上无法读取包含中文的路径
        优先使用 PIL/Pillow，它对中文路径支持更好
        """
        # 使用 resolve() 获取绝对路径，避免编码问题
        abs_path = file_path.resolve()
        
        # 方法1：使用 PIL/Pillow（优先，更好的中文路径支持）
        try:
            pil_img = Image.open(str(abs_path))
            
            # 转换为 numpy 数组
            if pil_img.mode == 'RGBA':
                img = np.array(pil_img)
                # PIL 返回 RGBA，转换为 BGRA（OpenCV格式）
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
            elif pil_img.mode == 'RGB':
                img = np.array(pil_img)
                # PIL 返回 RGB，转换为 BGRA
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGRA)
            elif pil_img.mode == 'L':
                # 灰度图
                img = np.array(pil_img)
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
            else:
                # 转换为 RGBA 再处理
                pil_img = pil_img.convert('RGBA')
                img = np.array(pil_img)
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
                
        except Exception as e:
            # 方法2：使用 np.fromfile + cv2.imdecode（备用方案）
            try:
                img_array = np.fromfile(str(abs_path), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise ValueError(f"无法解码图像")
                
                # 转换为BGRA格式
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
                elif img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
                elif img.shape[2] == 4:
                    pass  # 已经是BGRA格式
                    
            except Exception as e2:
                raise ValueError(
                    f"无法加载图像: {file_path}\n"
                    f"绝对路径: {abs_path}\n"
                    f"文件存在: {abs_path.exists()}\n"
                    f"方法1 (PIL) 错误: {e}\n"
                    f"方法2 (OpenCV) 错误: {e2}"
                )
        
        # 最终检查
        if img is None or len(img.shape) < 2:
            raise ValueError(f"图像加载失败或格式不正确: {file_path}")
        
        # 确保是 BGRA 格式
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        elif img.shape[2] == 4:
            pass  # 已经是BGRA格式
        else:
            raise ValueError(f"不支持的图像格式: {file_path} (shape: {img.shape})")
        
        return img
    
    def get_layer_hierarchy(self) -> List[Dict]:
        """获取图层层级信息"""
        return self.layer_hierarchy
    
    def get_layer_anchor(self, layer_name: str) -> Tuple[float, float]:
        """获取图层的锚点位置（相对于中心的归一化偏移）"""
        anchor = self.layer_anchors.get(layer_name, (0.0, 0.0))
        if isinstance(anchor, dict):
            return anchor['x'], anchor['y']
        return anchor

