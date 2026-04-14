"""
多数据源加载器
支持从多个数据集文件夹加载数据
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np


class MultiSourceDataLoader:
    """多数据源加载器"""
    
    def __init__(self, dataset_root: Path):
        """
        初始化多数据源加载器
        
        Args:
            dataset_root: 数据集根目录（皮影数据集/）
        """
        self.dataset_root = Path(dataset_root)
        self.sources = {}
        self._scan_sources()
    
    def _scan_sources(self):
        """扫描所有数据源"""
        if not self.dataset_root.exists():
            return
        
        # 1. 图层数据（主要数据源）
        layer_dir = self.dataset_root / "皮影肢体图层分解"
        if layer_dir.exists():
            self.sources['layers'] = {
                'path': layer_dir,
                'type': 'layers',
                'description': '皮影肢体图层分解数据'
            }
        
        # 2. Excel数据
        excel_file = self.dataset_root / "皮影戏数据集.xlsx"
        if excel_file.exists():
            self.sources['excel'] = {
                'path': excel_file,
                'type': 'excel',
                'description': 'Excel数据集文件'
            }
        
        # 3. HASPER数据集（Parquet格式）
        hasper_dir = self.dataset_root / "01.HASPER" / "01.HASPER"
        if hasper_dir.exists():
            train_file = hasper_dir / "train.parquet"
            val_file = hasper_dir / "validation.parquet"
            if train_file.exists() or val_file.exists():
                self.sources['hasper'] = {
                    'path': hasper_dir,
                    'type': 'parquet',
                    'description': 'HASPER数据集（Parquet格式）',
                    'train_file': train_file if train_file.exists() else None,
                    'val_file': val_file if val_file.exists() else None
                }
        
        # 4. Yale Shadow Puppets数据集（YOLO格式）
        yale_dir = self.dataset_root / "02.yale-shadow-puppets Dataset"
        if yale_dir.exists():
            train_images = yale_dir / "train" / "images"
            test_images = yale_dir / "test" / "images"
            if train_images.exists() or test_images.exists():
                self.sources['yale'] = {
                    'path': yale_dir,
                    'type': 'yolo',
                    'description': 'Yale Shadow Puppets数据集（YOLO格式）',
                    'train_images': train_images if train_images.exists() else None,
                    'test_images': test_images if test_images.exists() else None,
                    'train_labels': yale_dir / "train" / "labels" if (yale_dir / "train" / "labels").exists() else None,
                    'test_labels': yale_dir / "test" / "labels" if (yale_dir / "test" / "labels").exists() else None
                }
        
        # 5. Chinese Shadow Puppetry数据集（Processing代码+图层）
        chinese_dir = self.dataset_root / "03.Chinese-Shadow-puppetry-master" / "Chinese-Shadow-puppetry-master"
        if chinese_dir.exists():
            data_dir = chinese_dir / "data"
            if data_dir.exists():
                self.sources['chinese'] = {
                    'path': chinese_dir,
                    'type': 'processing',
                    'description': 'Chinese Shadow Puppetry数据集（Processing代码）',
                    'data_dir': data_dir
                }
    
    def get_available_sources(self) -> Dict:
        """获取所有可用的数据源"""
        return self.sources
    
    def load_layers_data(self) -> Dict[str, Path]:
        """加载图层数据"""
        if 'layers' not in self.sources:
            return {}
        layer_dir = self.sources['layers']['path']
        characters = {}
        for subdir in ["人物", "神怪"]:
            subdir_path = layer_dir / subdir
            if subdir_path.exists():
                for char_dir in subdir_path.iterdir():
                    if char_dir.is_dir():
                        characters[char_dir.name] = char_dir
        return characters
    
    def load_excel_data(self) -> Optional[pd.DataFrame]:
        """加载Excel数据"""
        if 'excel' not in self.sources:
            return None
        try:
            return pd.read_excel(str(self.sources['excel']['path']))
        except Exception as e:
            print(f"警告: 无法加载Excel数据: {e}")
            return None
    
    def load_hasper_data(self) -> Optional[Dict]:
        """加载HASPER数据集"""
        if 'hasper' not in self.sources:
            return None
        data = {}
        try:
            if self.sources['hasper']['train_file']:
                data['train'] = pd.read_parquet(self.sources['hasper']['train_file'])
            if self.sources['hasper']['val_file']:
                data['validation'] = pd.read_parquet(self.sources['hasper']['val_file'])
        except Exception as e:
            print(f"警告: 无法加载HASPER数据: {e}")
            return None
        return data if data else None
    
    def load_yale_data(self) -> Optional[Dict]:
        """加载Yale数据集"""
        if 'yale' not in self.sources:
            return None
        yale = self.sources['yale']
        data = {}
        if yale['train_images']:
            data['train'] = {
                'images': list(yale['train_images'].glob("*.jpg")),
                'labels': list(yale['train_labels'].glob("*.txt")) if yale['train_labels'] else [],
            }
            data['train']['count'] = len(data['train']['images'])
        if yale['test_images']:
            data['test'] = {
                'images': list(yale['test_images'].glob("*.jpg")),
                'labels': list(yale['test_labels'].glob("*.txt")) if yale['test_labels'] else [],
            }
            data['test']['count'] = len(data['test']['images'])
        return data if data else None
    
    def load_chinese_data(self) -> Optional[Dict]:
        """加载Chinese数据集"""
        if 'chinese' not in self.sources:
            return None
        data_dir = self.sources['chinese']['data_dir']
        layers = {}
        patterns = {
            'head': ['Head', 'head'],
            'body': ['Body', 'body'],
            'armL': ['ArmL', 'armL', 'fArmL', 'mArmL', 'hArmL'],
            'armR': ['ArmR', 'armR', 'fArmR', 'mArmR', 'hArmR'],
            'legL': ['LegL', 'legL', 'fLegL', 'mLegL', 'hLegL'],
            'legR': ['LegR', 'legR', 'fLegR', 'mLegR', 'hLegR']
        }
        for layer_type, pats in patterns.items():
            for p in pats:
                files = list(data_dir.glob(f"*{p}*.png"))
                if files:
                    layers[layer_type] = files
                    break
        return {'images': list(data_dir.glob("*.png")), 'audio': list(data_dir.glob("*.mp3")), 'layers': layers}
    
    def get_summary(self) -> Dict:
        """获取数据集摘要"""
        summary = {'dataset_root': str(self.dataset_root), 'available_sources': list(self.sources.keys()), 'sources_info': {}}
        for name, info in self.sources.items():
            s_info = {'type': info['type'], 'path': str(info['path'])}
            if name == 'layers':
                chars = self.load_layers_data()
                s_info.update({'characters_count': len(chars), 'character_names': list(chars.keys())})
            elif name == 'excel':
                df = self.load_excel_data()
                if df is not None:
                    s_info.update({'records_count': len(df), 'columns': df.columns.tolist()})
            elif name == 'hasper':
                d = self.load_hasper_data()
                if d:
                    s_info.update({'train_count': len(d.get('train', [])), 'val_count': len(d.get('validation', []))})
            elif name == 'yale':
                d = self.load_yale_data()
                if d:
                    s_info.update({'train_images': d.get('train', {}).get('count', 0), 'test_images': d.get('test', {}).get('count', 0)})
            elif name == 'chinese':
                d = self.load_chinese_data()
                if d:
                    s_info.update({'images_count': len(d.get('images', [])), 'audio_count': len(d.get('audio', [])), 'layers_count': len(d.get('layers', {}))})
            summary['sources_info'][name] = s_info
        return summary

