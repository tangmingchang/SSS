"""
动作库 - 存储典型动作模板和情感标签
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple


class ActionLibrary:
    """动作库管理器"""
    
    # 情感标签定义
    EMOTION_LABELS = {
        "悲怆": {
            "description": "悲伤、痛苦的情感",
            "characteristics": ["缓慢", "下压", "低姿态"],
            "color": "blue"
        },
        "欢快": {
            "description": "快乐、兴奋的情感",
            "characteristics": ["快速", "上挑", "跳跃"],
            "color": "yellow"
        },
        "打斗": {
            "description": "激烈、对抗的动作",
            "characteristics": ["快速", "大幅", "连续"],
            "color": "red"
        },
        "行走": {
            "description": "平稳的移动动作",
            "characteristics": ["规律", "交替", "节奏"],
            "color": "green"
        },
        "静止": {
            "description": "静止、等待的状态",
            "characteristics": ["稳定", "保持", "微动"],
            "color": "gray"
        },
        "挥手": {
            "description": "打招呼、告别的手势",
            "characteristics": ["摆动", "循环", "友好"],
            "color": "orange"
        },
        "鞠躬": {
            "description": "尊敬、致意的动作",
            "characteristics": ["前倾", "恢复", "庄重"],
            "color": "purple"
        }
    }
    
    def __init__(self, library_path: str = None):
        """
        初始化动作库
        
        Args:
            library_path: 动作库文件路径（JSON格式）
        """
        self.actions: Dict[str, np.ndarray] = {}
        self.emotion_mapping: Dict[str, str] = {}
        
        if library_path and Path(library_path).exists():
            self.load(library_path)
        else:
            self._initialize_default_actions()
    
    def _initialize_default_actions(self):
        """初始化默认动作模板"""
        # 创建一些基础动作模板（简化版，实际应该从数据中学习）
        input_dim = 51  # 17关节 * 3坐标
        
        # 悲怆动作：缓慢下压
        sorrowful = np.zeros((30, input_dim))
        for i in range(30):
            # 模拟缓慢下压动作
            sorrowful[i] = np.sin(np.pi * i / 30) * 0.3 - 0.5
        self.actions["悲怆"] = sorrowful
        self.emotion_mapping["悲怆"] = "悲怆"
        
        # 欢快动作：快速上挑
        joyful = np.zeros((30, input_dim))
        for i in range(30):
            # 模拟快速上挑动作
            joyful[i] = np.sin(2 * np.pi * i / 15) * 0.5 + 0.3
        self.actions["欢快"] = joyful
        self.emotion_mapping["欢快"] = "欢快"
        
        # 打斗动作：快速大幅变化
        fighting = np.zeros((30, input_dim))
        for i in range(30):
            # 模拟打斗动作
            fighting[i] = np.sin(3 * np.pi * i / 15) * 0.8 + np.random.randn(input_dim) * 0.1
        self.actions["打斗"] = fighting
        self.emotion_mapping["打斗"] = "打斗"
        
        # 行走动作：规律交替
        walking = np.zeros((30, input_dim))
        for i in range(30):
            # 模拟行走动作
            phase = i % 10
            walking[i] = np.sin(2 * np.pi * phase / 10) * 0.4
        self.actions["行走"] = walking
        self.emotion_mapping["行走"] = "行走"
        
        # 静止动作：保持稳定
        still = np.zeros((30, input_dim))
        still[:] = np.random.randn(input_dim) * 0.05  # 微小波动
        self.actions["静止"] = still
        self.emotion_mapping["静止"] = "静止"
        
        # 挥手动作：循环摆动
        waving = np.zeros((30, input_dim))
        for i in range(30):
            waving[i] = np.sin(2 * np.pi * i / 10) * 0.6
        self.actions["挥手"] = waving
        self.emotion_mapping["挥手"] = "挥手"
        
        # 鞠躬动作：前倾后恢复
        bowing = np.zeros((30, input_dim))
        for i in range(15):
            bowing[i] = -np.sin(np.pi * i / 15) * 0.5  # 前倾
        for i in range(15, 30):
            bowing[i] = -np.sin(np.pi * (30 - i) / 15) * 0.5  # 恢复
        self.actions["鞠躬"] = bowing
        self.emotion_mapping["鞠躬"] = "鞠躬"
    
    def add_action(self, name: str, template: np.ndarray, emotion: str = None):
        """
        添加动作模板
        
        Args:
            name: 动作名称
            template: 动作模板数组 [T, D]
            emotion: 情感标签
        """
        self.actions[name] = template
        if emotion:
            self.emotion_mapping[name] = emotion
    
    def get_action(self, name: str) -> np.ndarray:
        """获取动作模板"""
        return self.actions.get(name)
    
    def find_similar_action(self, segment: np.ndarray, top_k: int = 1) -> List[Tuple[str, float]]:
        """
        查找最相似的动作
        
        Args:
            segment: 动作片段 [T, D]
            top_k: 返回前k个最相似的动作
            
        Returns:
            [(动作名称, 相似度分数), ...]
        """
        similarities = []
        
        for action_name, template in self.actions.items():
            similarity = self._compute_similarity(segment, template)
            similarities.append((action_name, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def _compute_similarity(self, segment: np.ndarray, template: np.ndarray) -> float:
        """计算动作相似度"""
        # 对齐长度
        min_len = min(len(segment), len(template))
        seg = segment[:min_len]
        temp = template[:min_len]
        
        # 展平并归一化
        seg_flat = seg.flatten()
        temp_flat = temp.flatten()
        
        seg_norm = seg_flat / (np.linalg.norm(seg_flat) + 1e-6)
        temp_norm = temp_flat / (np.linalg.norm(temp_flat) + 1e-6)
        
        # 余弦相似度
        similarity = np.dot(seg_norm, temp_norm)
        
        return float(similarity)
    
    def get_emotion(self, action_name: str) -> str:
        """获取动作的情感标签"""
        return self.emotion_mapping.get(action_name, "未知")
    
    def save(self, output_path: str):
        """保存动作库到文件"""
        data = {
            "actions": {},
            "emotion_mapping": self.emotion_mapping,
            "emotion_labels": self.EMOTION_LABELS
        }
        
        for name, template in self.actions.items():
            data["actions"][name] = template.tolist()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self, library_path: str):
        """从文件加载动作库"""
        with open(library_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.actions = {}
        for name, template_list in data.get("actions", {}).items():
            self.actions[name] = np.array(template_list)
        
        self.emotion_mapping = data.get("emotion_mapping", {})
    
    def get_all_emotions(self) -> List[str]:
        """获取所有情感标签"""
        return list(self.EMOTION_LABELS.keys())








