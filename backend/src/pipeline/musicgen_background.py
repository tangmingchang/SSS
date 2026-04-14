"""
阶段二：MusicGen 戏曲风格背景音乐生成（可选）
当用户未上传背景音乐时，可用 Audiocraft MusicGen 生成戏曲氛围伴奏。
环境变量：ENABLE_MUSICGEN=1 启用；AUDIOCRAFT_MODEL=facebook/musicgen-small 可选；
AUDIOCRAFT_PROMPT_TEMPLATE=A|B|C 选内置模板（默认 A）；AUDIOCRAFT_PROMPT 可完全自定义提示词。

安装说明：
- 一般：pip install audiocraft
- Windows 若报「Microsoft Visual C++ 14.0 or greater is required」：是依赖 av 需编译导致。
  可不启用 MusicGen（不设 ENABLE_MUSICGEN），改用演出站上传背景音乐；或安装 VC++ 生成工具后重试；
  或先 conda install -c conda-forge av，再 pip install audiocraft --no-deps 并补全依赖。详见 docs/演出视频流水线实施路线图.md
"""
import os
from pathlib import Path


# 皮影戏/戏曲伴奏提示词模板（基于锣鼓经+文场，贴近戏班现场）
# 可通过 .env 的 AUDIOCRAFT_PROMPT 覆盖，或 AUDIOCRAFT_PROMPT_TEMPLATE=A|B|C 选模板
PROMPT_TEMPLATE_A = (
    "Traditional Chinese shadow puppetry (皮影戏) accompaniment, Chinese opera percussion ensemble. "
    "Foreground: guban (bangu + clapper) clear rhythmic cues, crisp wooden clicks. "
    "Midground: daluo and xiaoluo gongs with resonant tails, naobo cymbals with metallic swells. "
    "Background: subtle dagu drum support, occasional bangzi accents. "
    "Melodic layer: jinghu lead phrases and short interlude motifs, yueqin and sanxian comping. "
    "Lively stage performance feel, tight transitions, frequent 2-4 bar percussion breaks (过门), "
    "frequent short breaks and sparse sections for narration, no vocals, no modern synth, no cinematic strings. "
    "Moderate tempo 80-110 BPM, pentatonic traditional Chinese opera flavor, dry intimate recording with natural reverberation."
)
PROMPT_TEMPLATE_B = (
    "Chinese folk shadow puppet theatre music, energetic. "
    "Suona lead calls and responses with jinghu, supported by guban cues. "
    "Dense luogu (锣鼓) patterns: daluo, xiaoluo, naobo cymbals, dagu drum, bangzi. "
    "Fast upbeat, festive but theatrical, sharp articulation, strong rhythmic drive, no vocals, no EDM, no pop drums."
)
PROMPT_TEMPLATE_C = (
    "Chinese opera instrumental underscore for shadow puppetry. "
    "Jinghu lyrical lead, yueqin and sanxian gentle comping, light guban timekeeping. "
    "Occasional soft xiaoluo gong hits for transitions, minimal cymbals. "
    "Moderate tempo, elegant, traditional stage ambience, no vocals, no modern instruments."
)

# 默认使用模板 A（最像「皮影戏在演」、锣鼓经层次+留白给念白）
DEFAULT_PROMPT = PROMPT_TEMPLATE_A


def _inject_xformers_stub():
    """PyTorch CPU 环境下无 xformers 时，注入占位模块，用 PyTorch 原生 attention 回退。"""
    import sys
    import torch

    class _LowerTriangularMask:
        """占位：audiocraft 会 import xformers.ops.LowerTriangularMask，实际用 PyTorch 因果 mask 回退。"""
        pass

    class _Ops:
        LowerTriangularMask = _LowerTriangularMask
        unbind = staticmethod(torch.unbind)

        @staticmethod
        def memory_efficient_attention(q, k, v, attn_bias=None, p=None, scale=None, **kwargs):
            return torch.nn.functional.scaled_dot_product_attention(q, k, v, attn_mask=attn_bias, scale=scale)

    xformers = type(sys)("xformers")
    xformers.ops = _Ops()
    sys.modules["xformers"] = xformers
    sys.modules["xformers.ops"] = xformers.ops


def _patch_torchaudio_save_if_needed():
    """无 torchcodec 时用 scipy 写 WAV，避免 torchaudio 2.9+ 默认走 save_with_torchcodec 报错。"""
    import torch
    import torchaudio
    _orig = getattr(torchaudio, "save", None)
    if _orig is None:
        return

    def _save(path, src, sample_rate, **kwargs):
        err = None
        try:
            return _orig(path, src, sample_rate, **kwargs)
        except Exception as e:
            err = e
        if err and ("torchcodec" in str(err).lower() or "TorchCodec" in str(err)):
            from scipy.io import wavfile
            x = src.detach().cpu().numpy()
            if x.ndim == 3:
                x = x[0]
            if x.ndim == 2:
                x = x.T
            else:
                x = x.flatten()
            x = (x * 32767).clip(-32768, 32767).astype("int16")
            wavfile.write(path, sample_rate, x)
        else:
            raise err

    torchaudio.save = _save


def generate_background_music(
    duration_seconds: float,
    output_dir: Path,
    session_id: str,
    prompt: str = None,
) -> str:
    """
    使用 MusicGen 生成指定时长的戏曲风格伴奏 WAV。
    若未安装 audiocraft 或 ENABLE_MUSICGEN 未启用，返回空字符串。
    返回：生成的 WAV 文件路径；失败或未启用时返回 ""。
    """
    if os.environ.get("ENABLE_MUSICGEN", "").strip().lower() not in ("1", "true", "yes"):
        return ""
    if duration_seconds <= 0:
        return ""

    # 无 xformers 时（PyTorch CPU）：先注入占位，再导入 audiocraft 才不会报 No module named 'xformers'
    try:
        import xformers  # noqa: F401
    except ImportError:
        _inject_xformers_stub()

    try:
        import torch
        try:
            from audiocraft.models import MusicGen
        except ImportError:
            from audiocraft.models.musicgen import MusicGen
    except ImportError as e:
        print("[MusicGen] 未安装 audiocraft，跳过戏曲伴奏生成。可选：pip install audiocraft 或克隆 facebookresearch/audiocraft 后 pip install -e .", e)
        return ""

    model_name = os.environ.get("AUDIOCRAFT_MODEL", "facebook/musicgen-small").strip()
    if not model_name:
        model_name = "facebook/musicgen-small"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{session_id}_musicgen.wav"

    try:
        # 国内访问 Hugging Face 易中断，未配置时使用镜像
        if not os.environ.get("HF_ENDPOINT", "").strip():
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = MusicGen.get_pretrained(model_name, device=device)
        # 单次生成最长约 30 秒，若需要更长可分段生成后拼接（此处先按 30s 上限）
        gen_duration = min(max(1.0, duration_seconds), 30.0)
        model.set_generation_params(duration=gen_duration)
        env_prompt = os.environ.get("AUDIOCRAFT_PROMPT", "").strip()
        template_key = os.environ.get("AUDIOCRAFT_PROMPT_TEMPLATE", "").strip().upper()
        if prompt and prompt.strip():
            text_prompt = prompt.strip()
        elif env_prompt:
            text_prompt = env_prompt
        elif template_key == "B":
            text_prompt = PROMPT_TEMPLATE_B
        elif template_key == "C":
            text_prompt = PROMPT_TEMPLATE_C
        else:
            text_prompt = DEFAULT_PROMPT

        _patch_torchaudio_save_if_needed()
        with torch.no_grad():
            wav = model.generate([text_prompt], progress=False)

        if wav is None or (hasattr(wav, "numel") and wav.numel() == 0):
            return ""

        # wav: [B, C, T]，转为 [T] 或 [C,T] 并保存
        try:
            import torchaudio
            wav = wav.cpu()
            if wav.dim() == 3:
                wav = wav[0]
            if wav.dim() == 2:
                wav = wav.mean(dim=0)
            torchaudio.save(str(out_path), wav.unsqueeze(0), model.sample_rate)
        except Exception as e:
            print(f"[MusicGen] 保存 WAV 失败: {e}")
            return ""

        if out_path.exists():
            return str(out_path)
    except Exception as e:
        print(f"[MusicGen] 生成失败: {e}")
        return ""

    return ""
