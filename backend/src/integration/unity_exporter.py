"""
Unity引擎集成模块
导出BVH数据，定义骨骼层级，配置位置约束
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np


class UnityExporter:
    """Unity导出器"""
    
    def __init__(self):
        """初始化Unity导出器"""
        self.bone_hierarchy = self._define_bone_hierarchy()
        self.constraint_config = self._define_constraints()
    
    def _define_bone_hierarchy(self) -> Dict:
        """定义皮影骨骼层级结构"""
        return {
            "root": {
                "name": "Root",
                "position": (0, 0, 0),
                "children": ["spine", "left_shoulder", "right_shoulder", "left_hip", "right_hip"]
            },
            "spine": {
                "name": "Spine",
                "position": (0, 0.5, 0),
                "children": ["neck"]
            },
            "neck": {
                "name": "Neck",
                "position": (0, 0.3, 0),
                "children": ["head"]
            },
            "head": {
                "name": "Head",
                "position": (0, 0.2, 0),
                "children": []
            },
            "left_shoulder": {
                "name": "LeftShoulder",
                "position": (-0.3, 0.5, 0),
                "children": ["left_upper_arm"]
            },
            "left_upper_arm": {
                "name": "LeftUpperArm",
                "position": (-0.4, 0, 0),
                "children": ["left_forearm"]
            },
            "left_forearm": {
                "name": "LeftForearm",
                "position": (-0.3, 0, 0),
                "children": ["left_hand"]
            },
            "left_hand": {
                "name": "LeftHand",
                "position": (-0.2, 0, 0),
                "children": []
            },
            "right_shoulder": {
                "name": "RightShoulder",
                "position": (0.3, 0.5, 0),
                "children": ["right_upper_arm"]
            },
            "right_upper_arm": {
                "name": "RightUpperArm",
                "position": (0.4, 0, 0),
                "children": ["right_forearm"]
            },
            "right_forearm": {
                "name": "RightForearm",
                "position": (0.3, 0, 0),
                "children": ["right_hand"]
            },
            "right_hand": {
                "name": "RightHand",
                "position": (0.2, 0, 0),
                "children": []
            },
            "left_hip": {
                "name": "LeftHip",
                "position": (-0.2, -0.5, 0),
                "children": ["left_thigh"]
            },
            "left_thigh": {
                "name": "LeftThigh",
                "position": (0, -0.4, 0),
                "children": ["left_shin"]
            },
            "left_shin": {
                "name": "LeftShin",
                "position": (0, -0.4, 0),
                "children": ["left_foot"]
            },
            "left_foot": {
                "name": "LeftFoot",
                "position": (0, -0.2, 0),
                "children": []
            },
            "right_hip": {
                "name": "RightHip",
                "position": (0.2, -0.5, 0),
                "children": ["right_thigh"]
            },
            "right_thigh": {
                "name": "RightThigh",
                "position": (0, -0.4, 0),
                "children": ["right_shin"]
            },
            "right_shin": {
                "name": "RightShin",
                "position": (0, -0.4, 0),
                "children": ["right_foot"]
            },
            "right_foot": {
                "name": "RightFoot",
                "position": (0, -0.2, 0),
                "children": []
            }
        }
    
    def _define_constraints(self) -> Dict:
        """定义位置约束配置"""
        return {
            "position_constraints": [
                {
                    "source": "spine",
                    "target": "left_shoulder",
                    "type": "position",
                    "weight": 0.5,
                    "description": "左肩跟随脊柱运动"
                },
                {
                    "source": "spine",
                    "target": "right_shoulder",
                    "type": "position",
                    "weight": 0.5,
                    "description": "右肩跟随脊柱运动"
                },
                {
                    "source": "left_upper_arm",
                    "target": "left_forearm",
                    "type": "position",
                    "weight": 0.3,
                    "description": "衣袖摆动效果"
                },
                {
                    "source": "right_upper_arm",
                    "target": "right_forearm",
                    "type": "position",
                    "weight": 0.3,
                    "description": "衣袖摆动效果"
                },
                {
                    "source": "neck",
                    "target": "head",
                    "type": "position",
                    "weight": 0.2,
                    "description": "头部微动"
                }
            ],
            "rotation_constraints": [
                {
                    "joint": "left_shoulder",
                    "min_angle": -90,
                    "max_angle": 90,
                    "description": "肩部旋转限制"
                },
                {
                    "joint": "right_shoulder",
                    "min_angle": -90,
                    "max_angle": 90,
                    "description": "肩部旋转限制"
                }
            ]
        }
    
    def export_bvh_to_unity(self,
                            bvh_path: str,
                            output_dir: str,
                            character_name: str = "piying_character") -> Dict[str, str]:
        """
        将BVH文件导出为Unity可用的格式
        
        Args:
            bvh_path: BVH文件路径
            output_dir: 输出目录
            character_name: 角色名称
            
        Returns:
            导出文件路径字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 导出骨骼层级配置（JSON）
        hierarchy_file = output_dir / f"{character_name}_hierarchy.json"
        with open(hierarchy_file, 'w', encoding='utf-8') as f:
            json.dump(self.bone_hierarchy, f, indent=2, ensure_ascii=False)
        
        # 2. 导出约束配置（JSON）
        constraint_file = output_dir / f"{character_name}_constraints.json"
        with open(constraint_file, 'w', encoding='utf-8') as f:
            json.dump(self.constraint_config, f, indent=2, ensure_ascii=False)
        
        # 3. 复制BVH文件
        bvh_file = Path(bvh_path)
        unity_bvh_file = output_dir / f"{character_name}_motion.bvh"
        import shutil
        shutil.copy(bvh_file, unity_bvh_file)
        
        # 4. 生成Unity C#脚本模板
        csharp_script = self._generate_unity_script(character_name)
        script_file = output_dir / f"{character_name}_controller.cs"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(csharp_script)
        
        return {
            "hierarchy": str(hierarchy_file),
            "constraints": str(constraint_file),
            "bvh": str(unity_bvh_file),
            "script": str(script_file)
        }
    
    def _generate_unity_script(self, character_name: str) -> str:
        """生成Unity C#脚本模板"""
        return f'''using UnityEngine;
using System.Collections.Generic;

public class {character_name}Controller : MonoBehaviour
{{
    // BVH动画数据
    public TextAsset bvhFile;
    
    // 骨骼层级
    private Dictionary<string, Transform> boneMap = new Dictionary<string, Transform>();
    
    // 位置约束
    public List<PositionConstraint> positionConstraints = new List<PositionConstraint>();
    
    void Start()
    {{
        // 初始化骨骼映射
        InitializeBoneMap();
        
        // 加载BVH数据
        LoadBVHData();
    }}
    
    void Update()
    {{
        // 应用位置约束
        ApplyPositionConstraints();
    }}
    
    void InitializeBoneMap()
    {{
        // 根据层级配置初始化骨骼映射
        // TODO: 实现骨骼查找逻辑
    }}
    
    void LoadBVHData()
    {{
        // 解析BVH文件
        // TODO: 实现BVH解析逻辑
    }}
    
    void ApplyPositionConstraints()
    {{
        foreach (var constraint in positionConstraints)
        {{
            // 应用位置约束
            // TODO: 实现约束逻辑
        }}
    }}
}}

[System.Serializable]
public class PositionConstraint
{{
    public Transform source;
    public Transform target;
    public float weight = 0.5f;
}}
'''








