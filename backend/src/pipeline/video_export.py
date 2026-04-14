"""
阶段三：图生视频 + 与演出音频合成
默认：静态场景图（或角色+背景合成图）+ 念白与伴奏音频，经 ffmpeg 合成 MP4。
可选：设置 ANIMATEDIFF_SCRIPT 后，调用外部 AnimateDiff/Pose 脚本生成动态视频再与音频合成。
"""
import json
import os
import subprocess
from pathlib import Path


def _get_ffmpeg_path():
    """优先使用 imageio-ffmpeg，否则系统 ffmpeg。"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def build_video_from_image_and_audio(
    image_path: str,
    audio_path: str,
    output_mp4_path: str,
    width: int = None,
    height: int = None,
    fps: float = None,
    video_bitrate: str = None,
) -> bool:
    """
    使用 ffmpeg 将单张图片与音频合成为 MP4（图片持续整段音频时长）。
    width/height：可选，输出分辨率（偶数）；fps：帧率；video_bitrate：如 "2M"。
    成功返回 True，失败返回 False。
    """
    if not os.path.exists(image_path) or not os.path.exists(audio_path):
        return False
    ffmpeg = _get_ffmpeg_path()
    output_mp4_path = str(output_mp4_path)
    # libx264 要求宽高均为偶数
    vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if width is not None and height is not None:
        w, h = int(width), int(height)
        if w % 2:
            w -= 1
        if h % 2:
            h -= 1
        vf = f"scale={w}:{h}"
    try:
        cmd = [
            ffmpeg, "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-shortest",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
        ]
        if fps is not None and fps > 0:
            cmd.extend(["-r", str(round(fps, 2))])
        if video_bitrate:
            cmd.extend(["-b:v", str(video_bitrate)])
        cmd.append(output_mp4_path)
        ret = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if ret.returncode != 0:
            print(f"[video_export] ffmpeg 失败: {ret.stderr}")
            return False
        return os.path.exists(output_mp4_path)
    except subprocess.TimeoutExpired:
        print("[video_export] ffmpeg 超时")
        return False
    except Exception as e:
        print(f"[video_export] {e}")
        return False


def _run_animatediff_script(
    frame_path: str,
    character_path: str,
    audio_path: str,
    output_mp4_path: str,
    action_sequence: list = None,
    timeout_seconds: int = 600,
) -> str:
    """
    调用 ANIMATEDIFF_SCRIPT 生成动态视频。通过环境变量传入路径。
    脚本需将生成的 MP4 写入 output_mp4_path，成功返回 0。
    成功返回 output_mp4_path，失败返回 ""。
    """
    script_path = os.environ.get("ANIMATEDIFF_SCRIPT", "").strip()
    if not script_path or not os.path.isfile(script_path):
        return ""

    env = os.environ.copy()
    env["PIYING_FRAME_PATH"] = str(frame_path)
    env["PIYING_CHARACTER_PATH"] = str(character_path)
    env["PIYING_AUDIO_PATH"] = str(audio_path)
    env["PIYING_OUTPUT_MP4"] = str(output_mp4_path)
    actions_json_path = ""
    if action_sequence is not None:
        try:
            actions_json_path = str(Path(output_mp4_path).parent / "actions.json")
            with open(actions_json_path, "w", encoding="utf-8") as f:
                json.dump(action_sequence, f, ensure_ascii=False, indent=2)
            env["PIYING_ACTIONS_JSON"] = actions_json_path
        except Exception as e:
            print(f"[video_export] 写入 actions.json 失败: {e}")

    try:
        ret = subprocess.run(
            [os.environ.get("PYTHON", "python"), script_path],
            env=env,
            cwd=str(Path(script_path).parent),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        if ret.returncode != 0:
            print(f"[video_export] AnimateDiff 脚本退出码 {ret.returncode}: {ret.stderr or ret.stdout}")
            return ""
        if os.path.exists(output_mp4_path):
            return output_mp4_path
        print("[video_export] AnimateDiff 脚本未生成输出文件:", output_mp4_path)
        return ""
    except subprocess.TimeoutExpired:
        print("[video_export] AnimateDiff 脚本超时")
        return ""
    except Exception as e:
        print(f"[video_export] AnimateDiff 脚本执行异常: {e}")
        return ""


def build_placeholder_image(output_path: str, width: int = 1280, height: int = 720) -> bool:
    """生成一张占位图（纯色+简单文字），用于无背景图时导出视频。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (width, height), color=(40, 20, 10))
        draw = ImageDraw.Draw(img)
        font = None
        for path in ["arial.ttf", "Arial.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/msyh.ttc"]:
            try:
                font = ImageFont.truetype(path, 48)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        text = "皮影演出"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((width - tw) // 2, (height - th) // 2), text, fill=(220, 180, 100), font=font)
        img.save(output_path)
        return True
    except Exception as e:
        print(f"[video_export] 占位图生成失败: {e}")
        return False


def _get_assets_default_frame(backend_root: Path) -> str:
    """优先使用 Unity 皮影项目 Assets 中的默认场景图，用于无上传帧时的视频画面。"""
    assets = backend_root / "Assets"
    candidates = [
        assets / "PiYing" / "Mew" / "newbg.png",
        assets / "PiYing" / "Mew" / "bbg.png",
        assets / "PiYing" / "Mew" / "River.png",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return ""


def run_video_export(
    script: dict,
    output_dir: Path,
    session_id: str,
    music_file_path: str = None,
    background_image_path: str = None,
    character_image_path: str = None,
    frame_image_path: str = None,
    action_sequence: list = None,
    video_width: int = None,
    video_height: int = None,
    video_fps: float = None,
    video_bitrate: str = None,
    backend_root: Path = None,
) -> dict:
    """
    阶段三导出：先执行念白+音乐合成得到音频，再使用背景图（或占位图）与音频合成 MP4。
    若设置 ANIMATEDIFF_SCRIPT，则先调用该脚本生成动态视频，成功则用其作为成片，否则回退静态图+音频。
    返回 {"success": bool, "video_url": str 或 None, "audio_url": str 或 None, "error": str}
    """
    from src.pipeline.performance_export import run_performance_export

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) 阶段一：念白 + 音乐（含可选 MusicGen）
    perf = run_performance_export(script, output_dir, session_id, music_file_path)
    if not perf.get("success"):
        return {
            "success": False,
            "video_url": None,
            "audio_url": None,
            "error": perf.get("error", "演出音频生成失败"),
        }

    audio_path = output_dir / "performance.wav"
    if not audio_path.exists():
        return {"success": False, "video_url": None, "audio_url": perf.get("audio_url"), "error": "未找到合成音频文件"}

    # 2) 确定用于视频的帧图：场景图/舞台截图 > 背景图 > 角色图 > 占位图
    frame_path = output_dir / f"{session_id}_frame.png"
    if frame_image_path and os.path.exists(frame_image_path):
        try:
            from shutil import copy
            copy(frame_image_path, frame_path)
        except Exception:
            pass
    if not frame_path.exists() and background_image_path and os.path.exists(background_image_path):
        try:
            from shutil import copy
            copy(background_image_path, frame_path)
        except Exception:
            pass
    if not frame_path.exists() and character_image_path and os.path.exists(character_image_path):
        try:
            from shutil import copy
            copy(character_image_path, frame_path)
        except Exception:
            pass
    # 无任何上传图时优先使用 Unity 皮影 Assets 中的默认场景图
    if not frame_path.exists() and backend_root is not None:
        default_asset = _get_assets_default_frame(Path(backend_root))
        if default_asset and os.path.exists(default_asset):
            try:
                from shutil import copy
                copy(default_asset, frame_path)
            except Exception:
                pass
    if not frame_path.exists():
        build_placeholder_image(str(frame_path))

    if not frame_path.exists():
        return {
            "success": False,
            "video_url": None,
            "audio_url": perf.get("audio_url"),
            "error": "无法生成视频帧图",
        }

    character_path_str = str(character_image_path) if (character_image_path and os.path.exists(character_image_path)) else str(frame_path)
    video_path = output_dir / "performance.mp4"

    # 3) 可选：若配置了 AnimateDiff 脚本，调用生成动态视频
    animatediff_out = _run_animatediff_script(
        str(frame_path),
        character_path_str,
        str(audio_path),
        str(video_path),
        action_sequence=action_sequence,
    )

    # 4) 若 AnimateDiff 未产出视频，则静态图 + 音频 -> MP4（可调分辨率、码率）
    if not (animatediff_out and os.path.exists(animatediff_out)):
        if not build_video_from_image_and_audio(
            str(frame_path), str(audio_path), str(video_path),
            width=video_width, height=video_height, fps=video_fps, video_bitrate=video_bitrate,
        ):
            return {
                "success": False,
                "video_url": None,
                "audio_url": perf.get("audio_url"),
                "error": "ffmpeg 合成视频失败，请确认已安装 ffmpeg 或 imageio-ffmpeg",
            }

    return {
        "success": True,
        "video_url": f"/api/performance_audio/{session_id}/performance.mp4",
        "audio_url": perf.get("audio_url"),
    }
