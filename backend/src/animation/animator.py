"""
动画生成器 - 基于Wan-Animate的核心动画生成模块
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import cv2
from PIL import Image

from ..layers import LayerLoader, LayerComposer
from ..pose import PoseDetector, SkeletonExtractor
from ..models.pose_guider import PoseGuider
from ..models.relighting_lora import RelightingLoRA


class PiyingAnimator:
    """皮影动画生成器"""
    
    def __init__(self, config_path: str = "configs/model_config.yaml"):
        """
        初始化动画生成器
        
        Args:
            config_path: 配置文件路径
        """
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 初始化组件
        self.layer_loader = LayerLoader(self.config.get('layer_config_path', 'configs/layer_config.yaml'))
        self.layer_composer = LayerComposer(self.layer_loader)
        self.pose_detector = PoseDetector(
            model_path=self.config['pose_detector']['model_path'],
            detector_type=self.config['pose_detector']['type']
        )
        self.skeleton_extractor = SkeletonExtractor()
        
        # 初始化模型（实际使用时需要加载预训练模型）
        self.device = torch.device(self.config.get('device', 'cuda'))
        self.pose_guider = None  # 需要从配置文件加载
        self.relighting_lora = None  # 需要从配置文件加载
        
        # 数据路径
        self.characters_dir = Path(self.config.get('characters_dir', 'data/characters'))
        self.videos_dir = Path(self.config.get('videos_dir', 'data/videos'))
        self.outputs_dir = Path(self.config.get('outputs_dir', 'data/outputs'))
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
    
    def animate(self, 
               character_path: str,
               reference_video: str,
               output_path: str,
               width: Optional[int] = None,
               height: Optional[int] = None,
               length: Optional[int] = None,
               **kwargs) -> str:
        """
        生成动画视频
        
        Args:
            character_path: 角色图层目录路径
            reference_video: 参考视频路径
            output_path: 输出视频路径
            width: 输出宽度
            height: 输出高度
            length: 输出帧数
            **kwargs: 其他参数
            
        Returns:
            输出视频路径
        """
        # 加载角色图层
        print(f"加载角色图层: {character_path}")
        layers = self.layer_loader.load_character(character_path)
        
        # 检测参考视频中的姿态
        print(f"检测参考视频姿态: {reference_video}")
        reference_keypoints_list = self.pose_detector.detect_video(reference_video)
        
        # 限制帧数
        if length:
            reference_keypoints_list = reference_keypoints_list[:length]
        
        # 获取第一帧作为源图像
        cap = cv2.VideoCapture(reference_video)
        ret, first_frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"无法读取参考视频: {reference_video}")
        
        # 检测源图像的关键点
        source_keypoints = self.pose_detector.detect(first_frame)
        
        # 生成每一帧
        print("生成动画帧...")
        frames = []
        for idx, target_keypoints in enumerate(reference_keypoints_list):
            print(f"处理帧 {idx + 1}/{len(reference_keypoints_list)}")
            
            # 提取对齐的骨骼信号
            aligned_skeleton = self.skeleton_extractor.extract_spatial_aligned_skeleton(
                source_keypoints, target_keypoints
            )
            
            # 根据骨骼信号计算图层变换
            canvas_size = (
                width or self.config.get('default_width', 512),
                height or self.config.get('default_height', 768)
            )
            
            transformations = self.layer_composer.get_layer_positions(
                target_keypoints, canvas_size
            )
            
            # 合成当前帧
            frame = self.layer_composer.compose(layers, transformations)
            frames.append(frame)
        
        # 保存视频
        print(f"保存视频: {output_path}")
        self._save_video(frames, output_path, fps=self.config.get('default_fps', 8))
        
        return output_path
    
    def _save_video(self, frames: list, output_path: str, fps: int = 8):
        """
        保存帧序列为视频
        
        Args:
            frames: 帧列表
            output_path: 输出路径
            fps: 帧率
        """
        if not frames:
            raise ValueError("没有帧可以保存")
        
        height, width = frames[0].shape[:2]
        
        # 转换为BGR格式（OpenCV使用）。图层输出为 BGRA
        bgr_frames = [cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) if frame.shape[2] == 4 
                     else frame for frame in frames]
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        for frame in bgr_frames:
            out.write(frame)
        
        out.release()
        print(f"视频已保存: {output_path}")

