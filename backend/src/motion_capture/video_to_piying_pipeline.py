"""
视频到皮影动作的完整工作流
1. 使用 VIBE 提取 SMPL 参数（使用现成的 VIBE-master）
2. 转换为 BVH（使用现成的 smpl2bvh-main）
3. 骨架映射（人体 -> 皮影）
4. 风格化（戏曲化/木偶化）
"""

import os
import sys
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

# 导入新的集成模块
from .vibe_integration import VIBEPipeline, VIBEExtractor, SMPL2BVHConverter

# 添加 VIBE 和 smpl2bvh 到路径（用于直接调用）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / 'backend'
VIBE_DIR = BACKEND_DIR / 'VIBE-master'
SMPL2BVH_DIR = BACKEND_DIR / 'smpl2bvh-main'

if str(VIBE_DIR) not in sys.path:
    sys.path.insert(0, str(VIBE_DIR))
if str(SMPL2BVH_DIR) not in sys.path:
    sys.path.insert(0, str(SMPL2BVH_DIR))


class VideoToPiyingPipeline:
    """视频到皮影动作的完整管道"""
    
    PIYING_JOINTS = [
        "Root", "Hips", "Spine", "Spine1",
        "Neck", "Head",
        "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
        "RightShoulder", "RightArm", "RightForeArm", "RightHand",
        "LeftUpLeg", "LeftLeg", "LeftFoot",
        "RightUpLeg", "RightLeg", "RightFoot",
    ]
    
    # SMPL 24关节到皮影关节的映射
    SMPL_TO_PIYING_MAP = {
        # 根节点和脊柱
        0: 0,   # Pelvis -> Root
        3: 1,   # Spine1 -> Hips
        6: 2,   # Spine2 -> Spine
        9: 3,   # Spine3 -> Spine1
        12: 4,   # Neck -> Neck
        15: 5,   # Head -> Head
        
        # 左臂
        16: 6,   # Left_collar -> LeftShoulder
        18: 7,   # Left_shoulder -> LeftArm
        20: 8,   # Left_elbow -> LeftForeArm
        22: 9,   # Left_wrist -> LeftHand
        
        # 右臂
        17: 10,  # Right_collar -> RightShoulder
        19: 11,  # Right_shoulder -> RightArm
        21: 12,  # Right_elbow -> RightForeArm
        23: 13,  # Right_wrist -> RightHand
    }
    
    def __init__(self, vibe_model_path: Optional[str] = None, smpl_model_path: Optional[str] = None):
        """
        初始化管道
        
        Args:
            vibe_model_path: VIBE 模型路径（如果已下载）
            smpl_model_path: SMPL 模型路径（用于 smpl2bvh）
        """
        self.vibe_model_path = vibe_model_path
        self.smpl_model_path = smpl_model_path or str(SMPL2BVH_DIR / 'data' / 'smpl')
        
    # 注意: extract_smpl_from_video 和 smpl_to_bvh 方法已移除
    # 现在使用 vibe_integration.py 中的 VIBEPipeline 来处理
    # 这些方法的功能已集成到 process_video 中
    
    def map_skeleton_to_piying(self, bvh_path: str, output_path: str) -> str:
        """
        将人体 BVH 骨架映射到皮影骨架
        
        Args:
            bvh_path: 输入 BVH 文件路径
            output_path: 输出 BVH 文件路径
            
        Returns:
            输出 BVH 文件路径
        """
        # 读取 BVH 文件
        bvh_data = self._read_bvh(bvh_path)
        
        # 提取需要的关节
        piying_data = self._extract_piying_joints(bvh_data)
        
        # 应用骨架映射
        mapped_data = self._apply_skeleton_mapping(piying_data)
        
        # 写入新的 BVH 文件
        frametime = bvh_data.get('frametime', 1/30)
        fps = 1.0 / frametime if frametime > 0 else 30.0
        self._write_bvh(mapped_data, output_path, fps=fps)
        
        return output_path
    
    def stylize_motion(self, bvh_path: str, output_path: str, 
                      style_params: Optional[Dict] = None) -> str:
        """
        对动作进行皮影戏风格化
        
        Args:
            bvh_path: 输入 BVH 文件路径
            output_path: 输出 BVH 文件路径
            style_params: 风格化参数
            
        Returns:
            输出 BVH 文件路径
        """
        if style_params is None:
            style_params = {
                'hip_damping': 0.3,      # 髋部位移阻尼（减小移动）
                'arm_exaggeration': 1.5,  # 手臂动作夸张化
                'rhythm_pause': True,     # 节奏化停顿
                'arc_enhancement': True,  # 增强弧线运动
            }
        
        # 读取 BVH
        bvh_data = self._read_bvh(bvh_path)
        
        # 应用风格化
        stylized_data = self._apply_stylization(bvh_data, style_params)
        
        # 写入新的 BVH
        frametime = bvh_data.get('frametime', 1/30)
        fps = 1.0 / frametime if frametime > 0 else 30.0
        self._write_bvh(stylized_data, output_path, fps=fps)
        
        return output_path
    
    def process_video(self, video_path: str, output_dir: Optional[str] = None,
                     use_vibe: bool = True, stylize: bool = True) -> Dict[str, str]:
        """
        完整处理流程：视频 -> VIBE/SMPL -> BVH -> 映射 -> 风格化
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            use_vibe: 是否使用 VIBE（True=使用VIBE+smpl2bvh，False=使用MediaPipe后备方案）
            stylize: 是否应用风格化
            
        Returns:
            包含各阶段输出路径的字典
        """
        # 处理路径（支持相对路径和绝对路径，处理中文路径）
        video_path_str = str(video_path)
        video_path = Path(video_path_str)
        
        # 如果是相对路径，尝试多种方式解析
        if not video_path.is_absolute():
            # 先尝试相对于当前工作目录
            if video_path.exists():
                video_path = video_path.resolve()
            else:
                # 尝试相对于项目根目录
                project_root = Path(__file__).parent.parent.parent.parent
                alt_path = project_root / video_path_str
                if alt_path.exists():
                    video_path = alt_path.resolve()
                else:
                    # 尝试相对于 backend 目录
                    backend_dir = project_root / 'backend'
                    alt_path = backend_dir / video_path_str
                    if alt_path.exists():
                        video_path = alt_path.resolve()
                    else:
                        # 最后尝试 resolve（可能会失败）
                        try:
                            video_path = video_path.resolve()
                        except:
                            pass
        else:
            # 绝对路径，直接使用
            video_path = Path(video_path_str)
        
        # 检查文件是否存在
        if not video_path.exists():
            # 提供更详细的错误信息
            project_root = Path(__file__).parent.parent.parent.parent
            backend_dir = project_root / 'backend'
            videos_dir = backend_dir / 'data' / 'videos'
            
            error_msg = (
                f"视频文件不存在: {video_path}\n"
                f"当前工作目录: {Path.cwd()}\n"
                f"项目根目录: {project_root}\n"
                f"建议的视频目录: {videos_dir}\n"
                f"\n请检查:\n"
                f"1. 文件路径是否正确\n"
                f"2. 如果使用相对路径，请确保从正确的目录运行\n"
                f"3. 可以使用绝对路径，例如: D:\\大创-皮影\\backend\\data\\videos\\test1.mp4"
            )
            raise FileNotFoundError(error_msg)
        
        if output_dir is None:
            output_dir = video_path.parent / 'piying_motion'
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'video': str(video_path),
            'output_dir': str(output_dir),
        }
        
        # 步骤1: 提取动作数据并转换为 BVH
        if use_vibe:
            print("\n" + "="*60)
            print("步骤1: 使用 VIBE + smpl2bvh 提取动作")
            print("="*60)
            try:
                # 使用新的 VIBE 集成
                vibe_pipeline = VIBEPipeline(smpl_model_path=self.smpl_model_path)
                vibe_results = vibe_pipeline.process_video(
                    str(video_path),
                    str(output_dir),
                    fps=30.0
                )
                bvh_raw = Path(vibe_results['bvh_output'])
                results['vibe_output'] = vibe_results['vibe_output']
                results['bvh_raw'] = str(bvh_raw)
                bvh_path = str(bvh_raw)
                print(f"✓ VIBE 处理完成: {bvh_raw}")
            except Exception as e:
                print(f"⚠️  VIBE 处理失败: {e}")
                print("回退到 MediaPipe 方案...")
                use_vibe = False
        
        if not use_vibe:
            # 后备方案：使用 MediaPipe（简化版，准确度较低）
            print("\n" + "="*60)
            print("步骤1: 使用 MediaPipe 提取关键点（后备方案）")
            print("="*60)
            print("⚠️  注意: MediaPipe 只有 2D 关键点，准确度较低")
            print("建议配置 VIBE 环境以获得更好的效果")
            
            try:
                from .full_body_detector import FullBodyDetector
                from .bvh_24_joints import BVH24JointsConverter
                
                detector = FullBodyDetector()
                joints_sequence = detector.detect_video_24_joints(str(video_path))
                
                if not joints_sequence or len(joints_sequence) == 0:
                    raise ValueError('未检测到动作，请检查视频文件')
                
                converter = BVH24JointsConverter()
                bvh_raw = output_dir / 'raw_motion.bvh'
                converter.convert_24_joints_to_bvh(joints_sequence, str(bvh_raw), frame_rate=30.0)
                results['bvh_raw'] = str(bvh_raw)
                bvh_path = str(bvh_raw)
            except Exception as e:
                raise RuntimeError(f"MediaPipe 后备方案也失败: {e}")
        
        # 步骤2: 骨架映射（人体 -> 皮影）
        print("\n" + "="*60)
        print("步骤2: 映射到皮影骨架")
        print("="*60)
        bvh_mapped = output_dir / 'mapped_motion.bvh'
        self.map_skeleton_to_piying(bvh_path, str(bvh_mapped))
        results['bvh_mapped'] = str(bvh_mapped)
        
        # 步骤3: 风格化（戏曲化/木偶化）
        if stylize:
            print("\n" + "="*60)
            print("步骤3: 应用皮影戏风格化")
            print("="*60)
            bvh_final = output_dir / 'piying_motion.bvh'
            self.stylize_motion(str(bvh_mapped), str(bvh_final))
            results['bvh_final'] = str(bvh_final)
        else:
            results['bvh_final'] = str(bvh_mapped)
        
        print(f"\n{'='*60}")
        print(f"✓ 处理完成！输出目录: {output_dir}")
        print(f"{'='*60}")
        return results
    
    def _read_bvh(self, bvh_path: str) -> Dict:
        """读取 BVH 文件"""
        try:
            # 尝试使用 smpl2bvh 的 bvh 工具
            sys.path.insert(0, str(SMPL2BVH_DIR))
            from utils.bvh import load
            return load(bvh_path)
        except ImportError:
            # 如果无法导入，使用简化解析
            return self._parse_bvh_simple(bvh_path)
    
    def _parse_bvh_simple(self, bvh_path: str) -> Dict:
        """简化版 BVH 解析"""
        with open(bvh_path, 'r') as f:
            lines = f.readlines()
        
        # 解析骨架结构
        names = []
        parents = []
        offsets = []
        in_hierarchy = False
        in_motion = False
        frame_count = 0
        frametime = 1/30
        
        current_parent = -1
        parent_stack = []
        
        for line in lines:
            line = line.strip()
            if 'HIERARCHY' in line:
                in_hierarchy = True
                continue
            if 'MOTION' in line:
                in_hierarchy = False
                in_motion = True
                continue
            if 'Frames:' in line:
                frame_count = int(line.split(':')[1].strip())
                continue
            if 'Frame Time:' in line:
                frametime = float(line.split(':')[1].strip())
                continue
            
            if in_hierarchy:
                if 'ROOT' in line or 'JOINT' in line:
                    name = line.split()[-1]
                    names.append(name)
                    parents.append(current_parent)
                    parent_stack.append(current_parent)
                    current_parent = len(names) - 1
                    offsets.append([0, 0, 0])
                elif 'OFFSET' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        offsets[-1] = [float(parts[1]), float(parts[2]), float(parts[3])]
                elif '}' in line:
                    if parent_stack:
                        current_parent = parent_stack.pop()
            
            if in_motion and line and not line.startswith('Frames') and not line.startswith('Frame'):
                # 这是数据行，跳过解析（简化处理）
                break
        
        # 创建占位数据
        return {
            'names': names if names else self.PIYING_JOINTS,
            'parents': np.array(parents if parents else [-1, 0, 1, 2, 3, 4, 3, 6, 7, 8, 3, 10, 11, 12]),
            'offsets': np.array(offsets if offsets else [[0, 0, 0]] * len(names)),
            'rotations': np.zeros((max(frame_count, 100), len(names), 3)),
            'positions': np.zeros((max(frame_count, 100), 3)),
            'order': 'zyx',
            'frametime': frametime,
        }
    
    def _write_bvh(self, bvh_data: Dict, output_path: str, fps: float = 30.0):
        """写入 BVH 文件"""
        # 直接使用简化写入，确保格式正确
        # smpl2bvh 的 save 函数可能会把所有关节都写成 6 个通道，不符合 BVH 标准
        self._write_bvh_simple(bvh_data, output_path, fps)
    
    def _write_bvh_simple(self, bvh_data: Dict, output_path: str, fps: float):
        """简化版 BVH 写入"""
        names = bvh_data['names']
        parents = bvh_data['parents']
        offsets = bvh_data['offsets']
        rotations = bvh_data['rotations']
        positions = bvh_data['positions']
        order = bvh_data.get('order', 'zyx')
        frametime = bvh_data.get('frametime', 1.0/fps if fps > 0 else 1/30)
        
        with open(output_path, 'w') as f:
            # 写入 HIERARCHY
            f.write("HIERARCHY\n")
            self._write_joint_hierarchy(f, names, parents, offsets, order, 0, 0)
            
            # 写入 MOTION
            f.write("MOTION\n")
            f.write(f"Frames: {len(rotations)}\n")
            f.write(f"Frame Time: {frametime:.6f}\n")
            
            # 写入每帧数据
            for frame_idx in range(len(rotations)):
                frame_data = []
                
                # Root 节点：位置 + 旋转（6个通道）
                if len(positions.shape) == 3 and positions.shape[1] > 0:
                    frame_data.extend([
                        f"{positions[frame_idx, 0, 0]:.6f}",
                        f"{positions[frame_idx, 0, 1]:.6f}",
                        f"{positions[frame_idx, 0, 2]:.6f}"
                    ])
                elif len(positions.shape) == 2:
                    frame_data.extend([
                        f"{positions[frame_idx, 0]:.6f}",
                        f"{positions[frame_idx, 1]:.6f}",
                        f"{positions[frame_idx, 2]:.6f}"
                    ])
                else:
                    frame_data.extend(["0.000000", "0.000000", "0.000000"])
                
                # Root 旋转（ZYX顺序：Zrotation Xrotation Yrotation）
                if rotations.shape[1] > 0:
                    rot = rotations[frame_idx, 0]
                    frame_data.extend([f"{rot[2]:.6f}", f"{rot[0]:.6f}", f"{rot[1]:.6f}"])
                else:
                    frame_data.extend(["0.000000", "0.000000", "0.000000"])
                
                # 其他关节：只有旋转（3个通道：Zrotation Xrotation Yrotation）
                # 注意：BVH 标准中非 Root 关节不应该有位置通道
                for joint_idx in range(1, len(names)):
                    if joint_idx < rotations.shape[1]:
                        rot = rotations[frame_idx, joint_idx]
                        # ZYX 顺序：Zrotation Xrotation Yrotation
                        frame_data.extend([f"{rot[2]:.6f}", f"{rot[0]:.6f}", f"{rot[1]:.6f}"])
                    else:
                        frame_data.extend(["0.000000", "0.000000", "0.000000"])
                
                f.write(" ".join(frame_data) + "\n")
    
    def _write_joint_hierarchy(self, f, names, parents, offsets, order, joint_idx, indent):
        """递归写入关节层级"""
        indent_str = "\t" * indent
        name = names[joint_idx]
        
        if joint_idx == 0:
            f.write(f"{indent_str}ROOT {name}\n")
        else:
            f.write(f"{indent_str}JOINT {name}\n")
        
        f.write(f"{indent_str}{{\n")
        indent += 1
        indent_str = "\t" * indent
        
        # 写入 OFFSET
        offset = offsets[joint_idx]
        f.write(f"{indent_str}OFFSET {offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}\n")
        
        # 写入 CHANNELS
        if joint_idx == 0:
            # Root: 位置 + 旋转
            f.write(f"{indent_str}CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n")
        else:
            # 其他关节：只有旋转（注意：BVH 标准中非 Root 关节不应该有位置通道）
            f.write(f"{indent_str}CHANNELS 3 Zrotation Xrotation Yrotation\n")
        
        # 查找子关节
        children = [i for i, p in enumerate(parents) if p == joint_idx]
        
        if not children:
            # End Site
            f.write(f"{indent_str}End Site\n")
            f.write(f"{indent_str}{{\n")
            indent_str = "\t" * (indent + 1)
            f.write(f"{indent_str}OFFSET 0.000000 0.000000 0.000000\n")
            indent_str = "\t" * indent
            f.write(f"{indent_str}}}\n")
        else:
            # 递归写入子关节
            for child_idx in children:
                self._write_joint_hierarchy(f, names, parents, offsets, order, child_idx, indent)
        
        indent -= 1
        indent_str = "\t" * indent
        f.write(f"{indent_str}}}\n")
    
    def _extract_piying_joints(self, bvh_data: Dict) -> Dict:
        """提取皮影需要的关节"""
        # 从完整 BVH 中提取皮影骨架需要的关节
        # 这里假设输入已经是简化的人体骨架，直接返回
        return bvh_data
    
    def _apply_skeleton_mapping(self, bvh_data: Dict) -> Dict:
        """
        应用骨架映射：将人体骨架映射到皮影骨架
        
        皮影特点：
        - 主要关注上半身（头部、躯干、手臂）
        - 下半身简化或固定
        - 手臂动作更夸张
        """
        names = bvh_data['names']
        rotations = bvh_data['rotations'].copy()
        positions = bvh_data['positions'].copy()
        offsets = bvh_data['offsets'].copy()
        parents = bvh_data['parents'].copy()
        
        # 创建皮影骨架结构
        piying_names = self.PIYING_JOINTS.copy()
        piying_parents = np.array([
            -1, 0, 1, 2, 3, 4, 3, 6, 7, 8, 3, 10, 11, 12,
            1, 14, 15, 1, 17, 18
        ])
        piying_offsets = np.zeros((len(piying_names), 3))
        
        # 映射关节名称（简化处理，假设输入 BVH 已经有对应关节）
        name_mapping = {}
        for i, name in enumerate(names):
            # 尝试匹配关节名称
            name_lower = name.lower()
            if 'pelvis' in name_lower or 'hip' in name_lower:
                name_mapping[0] = i  # Root
            elif 'spine' in name_lower:
                if 'spine1' in name_lower or 'spine' == name_lower:
                    name_mapping[1] = i  # Hips
                elif 'spine2' in name_lower:
                    name_mapping[2] = i  # Spine
                elif 'spine3' in name_lower:
                    name_mapping[3] = i  # Spine1
            elif 'neck' in name_lower:
                name_mapping[4] = i  # Neck
            elif 'head' in name_lower:
                name_mapping[5] = i  # Head
            elif 'left' in name_lower and 'shoulder' in name_lower:
                name_mapping[6] = i  # LeftShoulder
            elif 'left' in name_lower and 'arm' in name_lower and 'fore' not in name_lower:
                name_mapping[7] = i  # LeftArm
            elif 'left' in name_lower and 'forearm' in name_lower or ('left' in name_lower and 'elbow' in name_lower):
                name_mapping[8] = i  # LeftForeArm
            elif 'left' in name_lower and 'wrist' in name_lower or ('left' in name_lower and 'hand' in name_lower):
                name_mapping[9] = i  # LeftHand
            elif 'right' in name_lower and 'shoulder' in name_lower:
                name_mapping[10] = i  # RightShoulder
            elif 'right' in name_lower and 'arm' in name_lower and 'fore' not in name_lower:
                name_mapping[11] = i  # RightArm
            elif 'right' in name_lower and 'forearm' in name_lower or ('right' in name_lower and 'elbow' in name_lower):
                name_mapping[12] = i  # RightForeArm
            elif 'right' in name_lower and 'wrist' in name_lower or ('right' in name_lower and 'hand' in name_lower):
                name_mapping[13] = i  # RightHand
            elif 'left' in name_lower and ('hip' in name_lower or 'upleg' in name_lower):
                name_mapping[14] = i  # LeftUpLeg
            elif 'left' in name_lower and ('knee' in name_lower or 'leg' in name_lower):
                name_mapping[15] = i  # LeftLeg
            elif 'left' in name_lower and ('ankle' in name_lower or 'foot' in name_lower):
                name_mapping[16] = i  # LeftFoot
            elif 'right' in name_lower and ('hip' in name_lower or 'upleg' in name_lower):
                name_mapping[17] = i  # RightUpLeg
            elif 'right' in name_lower and ('knee' in name_lower or 'leg' in name_lower):
                name_mapping[18] = i  # RightLeg
            elif 'right' in name_lower and ('ankle' in name_lower or 'foot' in name_lower):
                name_mapping[19] = i  # RightFoot

        # 创建映射后的旋转数据
        piying_rotations = np.zeros((rotations.shape[0], len(piying_names), 3))
        for piying_idx, human_idx in name_mapping.items():
            if human_idx < rotations.shape[1] and piying_idx < len(piying_names):
                piying_rotations[:, piying_idx, :] = rotations[:, human_idx, :]
        
        # 如果没有找到映射，使用默认值（保持初始姿态）
        # 对于未映射的关节，保持零旋转
        
        # 设置偏移量（简化处理）
        piying_offsets[0] = [0, 0, 0]  # Root
        piying_offsets[1] = [0, 10, 0]  # Hips
        piying_offsets[2] = [0, 15, 0]  # Spine
        piying_offsets[3] = [0, 15, 0]  # Spine1
        piying_offsets[4] = [0, 10, 0]  # Neck
        piying_offsets[5] = [0, 8, 0]   # Head
        piying_offsets[6] = [-8, 5, 0]  # LeftShoulder
        piying_offsets[7] = [-15, 0, 0] # LeftArm
        piying_offsets[8] = [-15, 0, 0] # LeftForeArm
        piying_offsets[9] = [-10, 0, 0] # LeftHand
        piying_offsets[10] = [8, 5, 0]  # RightShoulder
        piying_offsets[11] = [15, 0, 0] # RightArm
        piying_offsets[12] = [15, 0, 0] # RightForeArm
        piying_offsets[13] = [10, 0, 0] # RightHand
        piying_offsets[14] = [-5, -10, 0]   # LeftUpLeg
        piying_offsets[15] = [0, -20, 0]    # LeftLeg
        piying_offsets[16] = [0, -20, 0]   # LeftFoot
        piying_offsets[17] = [5, -10, 0]    # RightUpLeg
        piying_offsets[18] = [0, -20, 0]   # RightLeg
        piying_offsets[19] = [0, -20, 0]   # RightFoot

        # 确保 positions 形状正确
        if len(positions.shape) == 2:
            # positions 是 (frames, 3)，需要扩展为 (frames, 1, 3)
            positions_reshaped = positions[:, np.newaxis, :]
        elif positions.shape[1] == 1:
            positions_reshaped = positions
        else:
            # 只取第一个关节的位置（通常是根节点）
            positions_reshaped = positions[:, 0:1, :]
        
        return {
            'names': piying_names,
            'parents': piying_parents,
            'offsets': piying_offsets,
            'rotations': piying_rotations,
            'positions': positions_reshaped,
            'order': bvh_data.get('order', 'zyx'),
            'frametime': bvh_data.get('frametime', 1/30),
        }
    
    def _apply_stylization(self, bvh_data: Dict, style_params: Dict) -> Dict:
        """
        应用风格化处理
        
        Args:
            bvh_data: BVH 数据
            style_params: 风格化参数
            
        Returns:
            风格化后的 BVH 数据
        """
        rotations = bvh_data['rotations'].copy()
        positions = bvh_data['positions'].copy()
        
        # 1. 减小髋部位移
        if 'hip_damping' in style_params:
            damping = style_params['hip_damping']
            # Root 节点（索引0）的位移减小
            if len(positions.shape) == 3:
                # positions 是 (frames, joints, 3)
                positions[:, 0, 0] *= damping  # X
                positions[:, 0, 2] *= damping  # Z（前后）
                # Y（高度）保持，因为皮影在舞台上
            elif len(positions.shape) == 2:
                # positions 是 (frames, 3)
                positions[:, 0] *= damping  # X
                positions[:, 2] *= damping  # Z（前后）
        
        # 2. 增强手臂动作
        if 'arm_exaggeration' in style_params:
            exaggeration = style_params['arm_exaggeration']
            # 左臂关节（索引 6-9）
            for joint_idx in [6, 7, 8, 9]:
                if joint_idx < rotations.shape[1]:
                    rotations[:, joint_idx, :] *= exaggeration
            # 右臂关节（索引 10-13）
            for joint_idx in [10, 11, 12, 13]:
                if joint_idx < rotations.shape[1]:
                    rotations[:, joint_idx, :] *= exaggeration
        
        # 3. 节奏化停顿（在关键帧保持姿态）
        if style_params.get('rhythm_pause', False):
            num_frames = rotations.shape[0]
            # 每8帧做一次停顿（保持当前姿态）
            pause_frames = list(range(0, num_frames, 8))
            for i in pause_frames:
                if i + 1 < num_frames:
                    rotations[i+1] = rotations[i]
        
        # 4. 增强弧线运动（平滑插值）
        if style_params.get('arc_enhancement', False):
            # 使用平滑插值增强弧线感
            try:
                from scipy import signal
                if len(rotations.shape) == 3:
                    for joint_idx in range(rotations.shape[1]):
                        for axis in range(3):
                            window_len = min(11, max(5, len(rotations) // 4 * 2 + 1))
                            if window_len >= 5:
                                rotations[:, joint_idx, axis] = signal.savgol_filter(
                                    rotations[:, joint_idx, axis],
                                    window_length=window_len,
                                    polyorder=min(2, window_len - 1)
                                )
            except ImportError:
                # 如果没有 scipy，使用简单的移动平均
                if len(rotations.shape) == 3:
                    kernel_size = 3
                    for joint_idx in range(rotations.shape[1]):
                        for axis in range(3):
                            # 简单的移动平均
                            smoothed = np.convolve(
                                rotations[:, joint_idx, axis],
                                np.ones(kernel_size) / kernel_size,
                                mode='same'
                            )
                            rotations[:, joint_idx, axis] = smoothed
        
        return {
            **bvh_data,
            'rotations': rotations,
            'positions': positions,
        }
