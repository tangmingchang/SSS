"""
Shadowplay 皮影文生图模型推理（已停用，文生图现仅用通义万相 API）
基于 ModelScope z1292892952/shadowplay (ckpt-20)
"""

import os
from pathlib import Path
from typing import Optional, List
import uuid

# 默认模型路径（相对 backend）
DEFAULT_MODEL_DIR = "models/shadowplay"

# 所需权重文件（configuration.json 中声明）
REQUIRED_WEIGHTS = "20.safetensors"


def _resolve_model_dir(model_dir: Optional[str]) -> Path:
    """解析模型目录：支持 env SHADOWPLAY_MODEL_DIR、自定义路径、默认路径"""
    if model_dir and str(model_dir).strip():
        p = Path(model_dir).resolve()
        if p.exists():
            return p
    # 环境变量优先（便于指向实际下载位置）
    env_path = os.environ.get("SHADOWPLAY_MODEL_DIR", "").strip()
    if env_path:
        p = Path(env_path).resolve()
        if p.exists():
            return p
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir / DEFAULT_MODEL_DIR


class ShadowplayGenerator:
    """皮影文生图生成器"""

    def __init__(self, model_dir: Optional[str] = None):
        """
        Args:
            model_dir: 模型本地路径，若为 None 则使用 backend/models/shadowplay
                      也可通过环境变量 SHADOWPLAY_MODEL_DIR 指定
        """
        self.model_dir = _resolve_model_dir(model_dir)
        self._pipe = None

    def _ensure_loaded(self):
        """惰性加载 pipeline"""
        if self._pipe is not None:
            return
        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Shadowplay 模型目录不存在: {self.model_dir}\n"
                f"请运行: cd backend && python scripts/download_shadowplay.py\n"
                f"或设置环境变量 SHADOWPLAY_MODEL_DIR 指向已下载的模型目录"
            )
        weights = self.model_dir / REQUIRED_WEIGHTS
        if not weights.exists():
            raise FileNotFoundError(
                f"Shadowplay 权重文件缺失: {weights}\n"
                f"目录 {self.model_dir} 中需要 {REQUIRED_WEIGHTS}\n"
                f"若模型下载到其他位置，请在 .env 中添加: SHADOWPLAY_MODEL_DIR=实际路径"
            )
        from modelscope.pipelines import pipeline
        from modelscope.utils.constant import Tasks

        self._pipe = pipeline(
            task=Tasks.text_to_image_synthesis,
            model=str(self.model_dir),
        )

    def generate(
        self,
        prompt: str,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        num_images: int = 1,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> List:
        """
        根据文本描述生成皮影风格图像（最简提示词）。
        """
        self._ensure_loaded()
        enhanced_prompt = f"中国传统皮影戏风格，{prompt}"
        w = width if width else 512
        h = height if height else 512
        inp = {"text": enhanced_prompt}
        optional = {}
        if num_inference_steps:
            optional["num_inference_steps"] = num_inference_steps
        if guidance_scale:
            optional["guidance_scale"] = guidance_scale
        if num_images:
            optional["num_images_per_prompt"] = num_images
        optional["width"] = w
        optional["height"] = h
        inp.update(optional)

        output = self._pipe(inp)

        # 兼容不同 pipeline 输出格式
        imgs = []
        if isinstance(output, dict):
            imgs = output.get("output_imgs") or output.get("output_img") or output.get("images") or []
        elif hasattr(output, "images"):
            imgs = output.images if isinstance(output.images, list) else [output.images]
        elif hasattr(output, "output_imgs"):
            imgs = output.output_imgs
        # 直接返回 PIL Image
        if hasattr(output, "size") and hasattr(output, "save"):
            return [output]
        return imgs if (isinstance(imgs, list) and len(imgs) > 0) else []
