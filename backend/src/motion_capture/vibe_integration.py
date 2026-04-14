"""
VIBE + smpl2bvh 集成模块
使用现成的 VIBE-master 和 smpl2bvh-main 工具
"""

import os
import sys
import pickle
import subprocess
from pathlib import Path
from typing import Dict, Optional
import numpy as np

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / 'backend'
VIBE_DIR = BACKEND_DIR / 'VIBE-master'
SMPL2BVH_DIR = BACKEND_DIR / 'smpl2bvh-main'

# 添加到路径
if str(VIBE_DIR) not in sys.path:
    sys.path.insert(0, str(VIBE_DIR))
if str(SMPL2BVH_DIR) not in sys.path:
    sys.path.insert(0, str(SMPL2BVH_DIR))


class VIBEExtractor:
    """使用 VIBE 从视频提取 SMPL 参数"""
    
    def __init__(self):
        self.vibe_dir = VIBE_DIR
        self.check_vibe_available()
    
    def check_vibe_available(self):
        """检查 VIBE 是否可用"""
        demo_py = self.vibe_dir / 'demo.py'
        if not demo_py.exists():
            raise FileNotFoundError(
                f"VIBE demo.py 不存在: {demo_py}\n"
                "请确保 VIBE-master 目录在 backend 目录下"
            )
    
    def extract(self, video_path: str, output_dir: str) -> str:
        """
        从视频提取 SMPL 参数
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            
        Returns:
            vibe_output.pkl 文件路径
        """
        video_path = Path(video_path).resolve()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 切换到 VIBE 目录
        original_cwd = os.getcwd()
        os.chdir(str(self.vibe_dir))
        
        try:
            # 运行 VIBE demo
            cmd = [
                sys.executable, 'demo.py',
                '--vid_file', str(video_path),
                '--output_folder', str(output_dir.resolve()),
                '--no_render',  # 不渲染视频，只提取数据
            ]
            
            print(f"运行 VIBE: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"VIBE 运行失败:\n{error_msg}")
            
            # 查找输出的 pkl 文件
            video_name = video_path.stem
            vibe_output_pkl = output_dir / video_name / 'vibe_output.pkl'
            
            if not vibe_output_pkl.exists():
                # 尝试查找所有可能的 pkl 文件
                possible_pkls = list(output_dir.glob('**/vibe_output.pkl'))
                if possible_pkls:
                    vibe_output_pkl = possible_pkls[0]
                else:
                    raise FileNotFoundError(
                        f"找不到 VIBE 输出文件\n"
                        f"预期路径: {vibe_output_pkl}\n"
                        f"VIBE 输出:\n{result.stdout}"
                    )
            
            print(f"✓ VIBE 提取完成: {vibe_output_pkl}")
            return str(vibe_output_pkl)
            
        finally:
            os.chdir(original_cwd)


class SMPL2BVHConverter:
    """使用 smpl2bvh-main 将 SMPL 参数转换为 BVH"""
    
    def __init__(self, smpl_model_path: Optional[str] = None):
        """
        初始化转换器
        
        Args:
            smpl_model_path: SMPL 模型路径（默认使用 smpl2bvh-main/data/smpl）
        """
        self.smpl2bvh_dir = SMPL2BVH_DIR
        self.smpl_model_path = smpl_model_path or str(SMPL2BVH_DIR / 'data' / 'smpl')
        self.check_smpl2bvh_available()
    
    def check_smpl2bvh_available(self):
        """检查 smpl2bvh 是否可用"""
        smpl2bvh_py = self.smpl2bvh_dir / 'smpl2bvh.py'
        if not smpl2bvh_py.exists():
            raise FileNotFoundError(
                f"smpl2bvh.py 不存在: {smpl2bvh_py}\n"
                "请确保 smpl2bvh-main 目录在 backend 目录下"
            )
        
        # 检查 smplx 是否安装
        try:
            import smplx
        except ImportError:
            raise ImportError(
                "未安装 smplx，请运行: pip install smplx[all]"
            )
    
    def convert_vibe_output(self, vibe_pkl_path: str, output_bvh_path: str, fps: float = 30.0) -> str:
        """
        将 VIBE 输出转换为 BVH
        
        Args:
            vibe_pkl_path: VIBE 输出的 pkl 文件路径
            output_bvh_path: 输出 BVH 文件路径
            fps: 帧率
            
        Returns:
            BVH 文件路径
        """
        # 1. 转换格式
        converted_pkl = self._convert_vibe_format(vibe_pkl_path)
        
        # 2. 调用 smpl2bvh
        self._run_smpl2bvh(converted_pkl, output_bvh_path, fps)
        
        return output_bvh_path
    
    def _convert_vibe_format(self, vibe_pkl_path: str) -> str:
        """
        将 VIBE 输出格式转换为 smpl2bvh 需要的格式
        
        VIBE 格式:
        {
            person_id: {
                'pose': (N, 72),
                'trans': (N, 3),
                ...
            }
        }
        
        smpl2bvh 格式:
        {
            'smpl_poses': (N, 72),
            'smpl_trans': (N, 3),
            'smpl_scaling': (1,),
        }
        """
        print(f"转换 VIBE 输出格式: {vibe_pkl_path}")
        
        try:
            import joblib
            vibe_results = joblib.load(vibe_pkl_path)
        except Exception:
            with open(vibe_pkl_path, 'rb') as f:
                vibe_results = pickle.load(f)
        
        if len(vibe_results) == 0:
            raise ValueError("VIBE 输出中没有检测到任何人！")
        
        # 取第一个人
        person_id = list(vibe_results.keys())[0]
        person_data = vibe_results[person_id]
        
        print(f"使用人物 ID: {person_id}, 帧数: {len(person_data['pose'])}")
        
        # 提取数据
        smpl_poses = np.array(person_data['pose'])  # (N, 72)
        # VIBE 输出可能没有 trans，用 joints3d 的骨盆位置（第一关节）
        if 'trans' in person_data:
            smpl_trans = np.array(person_data['trans'])  # (N, 3)
        elif 'joints3d' in person_data:
            smpl_trans = np.array(person_data['joints3d'])[:, 0, :]  # 骨盆位置
        else:
            smpl_trans = np.zeros((len(smpl_poses), 3))
        smpl_scaling = np.array([1.0])
        
        # 创建 smpl2bvh 格式
        smpl2bvh_data = {
            'smpl_poses': smpl_poses,
            'smpl_trans': smpl_trans,
            'smpl_scaling': smpl_scaling,
        }
        
        # 保存到临时文件
        output_pkl = str(Path(vibe_pkl_path).parent / 'smpl2bvh_input.pkl')
        with open(output_pkl, 'wb') as f:
            pickle.dump(smpl2bvh_data, f)
        
        print(f"✓ 格式转换完成: {output_pkl}")
        return output_pkl
    
    def _run_smpl2bvh(self, input_pkl: str, output_bvh: str, fps: float):
        """运行 smpl2bvh 转换"""
        print(f"运行 smpl2bvh: {input_pkl} -> {output_bvh}")
        
        # 导入 smpl2bvh 函数
        sys.path.insert(0, str(self.smpl2bvh_dir))
        from smpl2bvh import smpl2bvh
        
        # 检查 SMPL 模型路径
        if not Path(self.smpl_model_path).exists():
            raise FileNotFoundError(
                f"SMPL 模型路径不存在: {self.smpl_model_path}\n"
                "请下载 SMPL 模型到该路径: https://smpl.is.tue.mpg.de/"
            )
        
        # 调用转换
        smpl2bvh(
            model_path=self.smpl_model_path,
            poses=input_pkl,
            output=output_bvh,
            mirror=False,
            model_type='smpl',
            gender='NEUTRAL',
            num_betas=10,
            fps=fps
        )
        
        print(f"✓ BVH 转换完成: {output_bvh}")


class VIBEPipeline:
    """完整的 VIBE + smpl2bvh 管道"""
    
    def __init__(self, smpl_model_path: Optional[str] = None):
        self.vibe_extractor = VIBEExtractor()
        self.bvh_converter = SMPL2BVHConverter(smpl_model_path)
    
    def process_video(self, video_path: str, output_dir: str, fps: float = 30.0) -> Dict[str, str]:
        """
        完整流程：视频 -> VIBE -> SMPL -> BVH
        
        Args:
            video_path: 输入视频路径
            output_dir: 输出目录
            fps: 帧率
            
        Returns:
            包含各阶段输出路径的字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 步骤 1: VIBE 提取 SMPL
        print("\n" + "="*60)
        print("步骤 1: 使用 VIBE 提取 SMPL 参数")
        print("="*60)
        vibe_pkl = self.vibe_extractor.extract(video_path, str(output_dir))
        
        # 步骤 2: 转换为 BVH
        print("\n" + "="*60)
        print("步骤 2: 转换为 BVH")
        print("="*60)
        output_bvh = output_dir / f"{Path(video_path).stem}_vibe.bvh"
        self.bvh_converter.convert_vibe_output(str(vibe_pkl), str(output_bvh), fps)
        
        return {
            'vibe_output': vibe_pkl,
            'bvh_output': str(output_bvh),
            'output_dir': str(output_dir),
        }
