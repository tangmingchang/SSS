"""
动作捕捉模块 - 网站使用 full_body_detector / bvh_24_joints / realtime_pose_mapper。
VIBE/smpl2bvh 已移除，若需视频转 BVH 可自行恢复对应仓库。
"""

# VIBE + smpl2bvh 方案（可选，需 VIBE-master、smpl2bvh-main 目录）
try:
    from .vibe_integration import VIBEPipeline, VIBEExtractor, SMPL2BVHConverter
    from .video_to_piying_pipeline import VideoToPiyingPipeline
    _has_vibe = True
except (ImportError, FileNotFoundError, OSError):
    VIBEPipeline = VIBEExtractor = SMPL2BVHConverter = VideoToPiyingPipeline = None
    _has_vibe = False

# 旧接口（网站当前使用）
try:
    from .mediapipe_detector import MediaPipeHandDetector
    from .bvh_converter import BVHConverter
    from .keypoint_mapper import KeypointMapper
    from .full_body_detector import FullBodyDetector
    from .bvh_24_joints import BVH24JointsConverter
except ImportError:
    MediaPipeHandDetector = BVHConverter = KeypointMapper = FullBodyDetector = BVH24JointsConverter = None

__all__ = [
    'VIBEPipeline', 'VIBEExtractor', 'SMPL2BVHConverter', 'VideoToPiyingPipeline',
    'MediaPipeHandDetector', 'BVHConverter', 'KeypointMapper',
    'FullBodyDetector', 'BVH24JointsConverter',
]

