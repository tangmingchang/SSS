"""
关键点映射器
将MediaPipe手部关键点映射到皮影角色的骨骼层级
"""

import numpy as np
from typing import Dict, List, Tuple
from ..layers import LayerLoader


class KeypointMapper:
    """关键点映射器"""
    
    def __init__(self, layer_config_path: str = "configs/layer_config.yaml"):
        """
        初始化关键点映射器
        
        Args:
            layer_config_path: 图层配置文件路径
        """
        self.layer_loader = LayerLoader(layer_config_path)
        self.layer_hierarchy = self.layer_loader.get_layer_hierarchy()
        
        # 定义手部关键点到皮影骨骼的映射关系
        # 这是一个简化的映射，实际需要根据皮影戏的特点调整
        self.hand_to_puppet_mapping = {
            # 手腕 -> 上身（控制整体位置）
            'WRIST': '上身',
            # 拇指 -> 右手控制
            'THUMB_TIP': '右手',
            # 食指 -> 左手控制
            'INDEX_FINGER_TIP': '左手',
            # 其他手指可以映射到其他部位
        }
    
    def map_hand_to_puppet(self, 
                           hand_keypoints: Dict,
                           puppet_layers: Dict[str, np.ndarray]) -> Dict[str, Dict]:
        """
        将手部关键点映射到皮影角色的图层变换
        
        Args:
            hand_keypoints: MediaPipe手部关键点数据
            puppet_layers: 皮影角色图层字典
            
        Returns:
            图层变换参数字典
        """
        transformations = {}
        
        landmarks_2d = hand_keypoints.get('landmarks_2d', [])
        landmarks_3d = hand_keypoints.get('landmarks_3d', [])
        
        if not landmarks_2d or not landmarks_3d:
            return transformations
        
        # 获取手腕位置（控制整体位置）
        wrist_2d = landmarks_2d[0]
        wrist_3d = landmarks_3d[0]
        
        # 计算手部姿态（简化）
        # 使用拇指和食指的方向
        if len(landmarks_2d) >= 9:
            thumb_tip = landmarks_2d[4]
            index_tip = landmarks_2d[8]
            
            # 计算方向向量
            direction = np.array([
                index_tip['x'] - thumb_tip['x'],
                index_tip['y'] - thumb_tip['y']
            ])
            
            # 计算旋转角度
            angle = np.degrees(np.arctan2(direction[1], direction[0]))
        else:
            angle = 0.0
        
        # 映射到图层
        for layer_info in self.layer_hierarchy:
            layer_name = layer_info['name']
            
            # 根据图层类型应用不同的变换
            if layer_name == '上身':
                transformations[layer_name] = {
                    'translation': (wrist_2d['x'], wrist_2d['y']),
                    'rotation': angle,
                    'scale': 1.0
                }
            elif '手' in layer_name:
                # 手部图层根据手指位置调整
                if '左' in layer_name:
                    # 左手使用食指
                    if len(landmarks_2d) >= 9:
                        finger_tip = landmarks_2d[8]
                        transformations[layer_name] = {
                            'translation': (finger_tip['x'], finger_tip['y']),
                            'rotation': angle + 45,  # 调整角度
                            'scale': 1.0
                        }
                elif '右' in layer_name:
                    # 右手使用拇指
                    if len(landmarks_2d) >= 5:
                        thumb_tip = landmarks_2d[4]
                        transformations[layer_name] = {
                            'translation': (thumb_tip['x'], thumb_tip['y']),
                            'rotation': angle - 45,
                            'scale': 1.0
                        }
            else:
                # 其他图层使用默认变换
                transformations[layer_name] = {
                    'translation': (wrist_2d['x'], wrist_2d['y']),
                    'rotation': 0.0,
                    'scale': 1.0
                }
        
        return transformations
    
    def map_bvh_to_puppet(self, 
                         bvh_data: Dict,
                         frame_idx: int,
                         puppet_layers: Dict[str, np.ndarray]) -> Dict[str, Dict]:
        """
        将BVH数据映射到皮影角色的图层变换
        
        Args:
            bvh_data: BVH数据字典
            frame_idx: 帧索引
            puppet_layers: 皮影角色图层字典
            
        Returns:
            图层变换参数字典
        """
        transformations = {}
        
        if frame_idx >= len(bvh_data['motion_data']):
            return transformations
        
        # 获取当前帧的BVH数据
        frame_data = bvh_data['motion_data'][frame_idx]
        
        # BVH数据格式：[Xposition Yposition Zposition Zrotation Xrotation Yrotation ...]
        if len(frame_data) >= 6:
            position = frame_data[0:3]
            rotation = frame_data[3:6]
            
            # 映射到图层
            for layer_info in self.layer_hierarchy:
                layer_name = layer_info['name']
                
                # 根据图层层级应用变换
                transformations[layer_name] = {
                    'translation': (position[0], position[1]),
                    'rotation': rotation[2],  # Z旋转
                    'scale': 1.0
                }
        
        return transformations








