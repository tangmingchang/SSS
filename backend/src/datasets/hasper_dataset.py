"""HASPER数据集加载器"""
import pandas as pd
import torch
from torch.utils.data import Dataset
from PIL import Image
from pathlib import Path
import json
import cv2
import numpy as np
from typing import Dict, Optional


class HASPERDataset(Dataset):
    """HASPER数据集"""
    
    def __init__(
        self,
        parquet_path: str,
        dataset_root: Optional[str] = None,
        transform=None,
        img_size=(512, 768)
    ):
        self.dataset_root = Path(dataset_root) if dataset_root else Path(parquet_path).parent.parent.parent
        self.transform = transform
        self.img_size = img_size
        
        # 加载Parquet数据
        self.df = pd.read_parquet(parquet_path)
        print(f"加载HASPER数据: {len(self.df)} 条记录")
        print(f"列名: {self.df.columns.tolist()}")
        
        # 解析图像路径
        self.samples = []
        for idx, row in self.df.iterrows():
            img_info = row['image']
            label = row.get('label', 0)
            
            if isinstance(img_info, dict):
                img_path = img_info.get('path', '')
                
                # 修正路径（从绝对路径提取相对路径）
                if '/HaSPeR/' in img_path or '/HaSPeR/data/' in img_path:
                    # 提取相对路径部分
                    if '/HaSPeR/data/' in img_path:
                        rel_path = img_path.split('/HaSPeR/data/')[-1]
                    elif '/HaSPeR/' in img_path:
                        rel_path = img_path.split('/HaSPeR/')[-1]
                    else:
                        rel_path = img_path.split('/')[-1]
                    
                    # 尝试多个可能的路径
                    possible_paths = [
                        self.dataset_root / "01.HASPER" / "01.HASPER" / "data" / rel_path,
                        self.dataset_root / "01.HASPER" / rel_path,
                        Path(img_path),  # 原始路径
                    ]
                    
                    img_path = None
                    for p in possible_paths:
                        if p.exists():
                            img_path = str(p)
                            break
                    
                    # 如果还是找不到，尝试只使用文件名
                    if not img_path:
                        filename = Path(rel_path).name
                        for p in self.dataset_root.rglob(filename):
                            if p.exists():
                                img_path = str(p)
                                break
                
                if img_path and Path(img_path).exists():
                    self.samples.append({
                        'image_path': img_path,
                        'label': label,
                        'id': idx
                    })
                elif img_info.get('bytes'):
                    self.samples.append({
                        'image_bytes': img_info['bytes'],
                        'label': label,
                        'id': idx
                    })
        
        print(f"有效样本: {len(self.samples)} / {len(self.df)}")
        
        # 默认变换
        if self.transform is None:
            import torchvision.transforms as transforms
            self.transform = transforms.Compose([
                transforms.Resize(self.img_size),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ])
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # 加载图像
        if 'image_path' in sample:
            img = Image.open(sample['image_path']).convert('RGB')
        elif 'image_bytes' in sample:
            import io
            img = Image.open(io.BytesIO(sample['image_bytes'])).convert('RGB')
        else:
            raise ValueError(f"样本 {idx} 没有有效的图像数据")
        
        # 应用变换
        img_tensor = self.transform(img)
        
        return {
            'image': img_tensor,
            'label': torch.tensor(sample['label'], dtype=torch.long),
            'id': sample['id']
        }

