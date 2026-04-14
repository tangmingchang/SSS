"""Yale数据集加载器"""
import torch
from torch.utils.data import Dataset
from PIL import Image
from pathlib import Path
import cv2
import numpy as np
import torchvision.transforms as transforms


class YaleDataset(Dataset):
    """Yale Shadow Puppets数据集（YOLO格式）"""
    
    def __init__(self, dataset_root: str, split='train', img_size=(512, 768)):
        self.dataset_root = Path(dataset_root)
        self.split = split
        self.img_size = img_size
        
        # 加载图像和标签
        images_dir = self.dataset_root / split / "images"
        labels_dir = self.dataset_root / split / "labels"
        
        self.image_files = sorted(list(images_dir.glob("*.jpg")))
        self.label_files = []
        
        for img_file in self.image_files:
            label_file = labels_dir / (img_file.stem + ".txt")
            if label_file.exists():
                self.label_files.append(label_file)
            else:
                self.label_files.append(None)
        
        print(f"Yale {split}数据集: {len(self.image_files)} 张图像")
        
        # 图像变换
        self.transform = transforms.Compose([
            transforms.Resize(img_size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5]),
        ])
    
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        img_file = self.image_files[idx]
        label_file = self.label_files[idx]
        
        # 加载图像
        img = Image.open(img_file).convert('RGB')
        img_tensor = self.transform(img)
        
        # 加载标签（YOLO格式）
        boxes = []
        if label_file:
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        boxes.append([class_id, x_center, y_center, width, height])
        
        return {
            'image': img_tensor,
            'boxes': boxes,
            'image_path': str(img_file)
        }








