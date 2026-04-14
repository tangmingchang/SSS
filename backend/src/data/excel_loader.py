"""
Excel数据集加载器
加载和解析皮影戏数据集.xlsx文件
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json


class ExcelDatasetLoader:
    """Excel数据集加载器"""
    
    def __init__(self, excel_path: str):
        """
        初始化Excel加载器
        
        Args:
            excel_path: Excel文件路径
        """
        self.excel_path = Path(excel_path)
        self.df = None
        self._load()
    
    def _load(self):
        """加载Excel文件"""
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {self.excel_path}")
        
        try:
            self.df = pd.read_excel(self.excel_path)
        except Exception as e:
            raise ValueError(f"无法读取Excel文件: {e}")
    
    def get_dataframe(self) -> pd.DataFrame:
        """获取DataFrame"""
        return self.df
    
    def get_columns(self) -> List[str]:
        """获取列名"""
        return self.df.columns.tolist()
    
    def get_records(self) -> List[Dict]:
        """获取所有记录（字典列表）"""
        return self.df.to_dict('records')
    
    def find_character_records(self, character_name: str) -> List[Dict]:
        """查找特定角色的记录"""
        records = []
        for col in self.df.columns:
            mask = self.df[col].astype(str).str.contains(character_name, na=False, case=False)
            if mask.any():
                records.extend(self.df[mask].to_dict('records'))
        # 去重
        seen = set()
        unique = []
        for r in records:
            key = str(sorted(r.items()))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique
    
    def get_statistics(self) -> Dict:
        """获取数据集统计信息"""
        return {
            'total_records': len(self.df),
            'total_columns': len(self.df.columns),
            'columns': self.df.columns.tolist(),
            'data_types': self.df.dtypes.to_dict(),
            'missing_values': self.df.isnull().sum().to_dict(),
            'shape': self.df.shape
        }
    
    def export_to_json(self, output_path: str):
        """
        导出为JSON格式
        
        Args:
            output_path: 输出文件路径
        """
        data = {
            'statistics': self.get_statistics(),
            'records': self.get_records()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def merge_with_characters(self, characters: Dict[str, Path]) -> Dict:
        """
        与角色图层数据合并
        
        Args:
            characters: 角色名称到目录路径的字典
            
        Returns:
            合并后的数据字典
        """
        merged = {}
        
        for char_name, char_dir in characters.items():
            char_records = self.find_character_records(char_name)
            
            merged[char_name] = {
                'character_name': char_name,
                'character_dir': str(char_dir),
                'excel_records': char_records,
                'has_excel_data': len(char_records) > 0
            }
        
        return merged

