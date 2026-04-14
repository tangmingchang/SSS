"""
演出导出流水线（阶段一）：剧本台词 → TTS 念白 → 与背景音乐混音 → 输出完整音频
优先 ChatTTS（可配置本地模型路径 CHATTTS_MODEL_DIR），失败时自动回退到 edge-tts（无需下载大模型）。
"""
import os
import asyncio
from pathlib import Path


def _collect_lines_from_script(script) -> list:
    """从剧本中按场景顺序收集所有台词句子（用于 TTS）。"""
    if not script or not isinstance(script, dict):
        return []
    scenes = script.get("scenes") or []
    lines = []
    for s in sorted(scenes, key=lambda x: x.get("scene_number", 0)):
        for line in (s.get("lines") or []):
            if isinstance(line, str) and line.strip():
                lines.append(line.strip())
    return lines


def _generate_tts_edge_tts(lines: list, out_path: str):
    """
    使用 edge-tts（微软在线 TTS）合成念白，无需本地模型。需网络。
    多句分别合成 MP3 后用 pydub 拼接并转为 WAV。需要系统已安装 ffmpeg 并加入 PATH。
    返回 (True, None) 成功；(False, 错误信息) 失败。
    """
    try:
        import edge_tts
        from pydub import AudioSegment

        async def _run():
            segments = []
            for i, text in enumerate(lines):
                if not text.strip():
                    continue
                tmp_mp3 = out_path + f".tmp_{i}.mp3"
                comm = edge_tts.Communicate(text.strip(), "zh-CN-XiaoxiaoNeural")
                await comm.save(tmp_mp3)
                segments.append(AudioSegment.from_mp3(tmp_mp3))
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
            if not segments:
                return False, "无有效台词"
            combined = segments[0]
            for s in segments[1:]:
                combined += s
            combined.export(out_path, format="wav")
            return True, None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
    except OSError as e:
        errno = getattr(e, "errno", None)
        winerror = getattr(e, "winerror", None)
        msg = str(e)
        if errno == 2 or winerror == 2 or "找不到" in msg or "cannot find" in msg.lower():
            hint = "edge-tts 回退需要 ffmpeg 处理音频。请安装 ffmpeg 并加入系统 PATH（Windows 可用: choco install ffmpeg，或从 https://ffmpeg.org 下载）。"
            print(f"[TTS] edge-tts 回退失败: {e}")
            print(f"[TTS] {hint}")
            return False, hint
        print(f"[TTS] edge-tts 回退失败: {e}")
        return False, msg
    except Exception as e:
        print(f"[TTS] edge-tts 回退失败: {e}")
        return False, str(e)


def generate_tts_audio(lines: list, output_dir: Path, session_id: str):
    """
    将台词列表合成为一条念白 WAV。优先 ChatTTS（可设 CHATTTS_MODEL_DIR 指定本地模型），
    失败则自动使用 edge-tts（需网络，无需模型下载）。
    返回 (wav_path, None) 成功；( "", 错误信息 ) 失败。
    """
    if not lines:
        return "", "无台词"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{session_id}_tts.wav"

    # 1) 尝试 ChatTTS（支持本地模型路径，避免下载失败）
    chattts_ok = False
    local_path = os.environ.get("CHATTTS_MODEL_DIR", "").strip()
    # 国内访问 Hugging Face 易超时，未配置时使用镜像（与 MusicGen 一致）
    if not os.environ.get("HF_ENDPOINT", "").strip():
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    try:
        import numpy as np
        import ChatTTS

        chat = ChatTTS.Chat()
        if hasattr(chat, "load"):
            # load() 部分版本支持 custom_path，先尝试本地路径
            if local_path and os.path.isdir(local_path):
                try:
                    chat.load(compile=False, source="custom", custom_path=local_path)
                except TypeError:
                    chat.load(compile=False)
            else:
                chat.load(compile=False)
        else:
            if local_path and os.path.isdir(local_path):
                chat.load_models(compile=False, source="local", local_path=local_path)
            else:
                chat.load_models(compile=False)
        wavs = chat.infer(lines)
        if wavs is None:
            raise ValueError("ChatTTS infer 返回空")
        if not isinstance(wavs, (list, tuple)):
            wavs = [wavs]
        to_concat = []
        for w in wavs:
            if w is None or (hasattr(w, "size") and w.size == 0):
                continue
            w = np.asarray(w)
            if w.ndim == 2:
                w = w.flatten()
            to_concat.append(w)
        if not to_concat:
            raise ValueError("无有效音频")
        concatenated = np.concatenate(to_concat, axis=0)
        if concatenated.size == 0:
            raise ValueError("拼接后为空")
        try:
            import torch
            import torchaudio
            tensor = torch.from_numpy(concatenated)
            if tensor.dim() == 1:
                tensor = tensor.unsqueeze(0)
            torchaudio.save(str(out_path), tensor, 24000)
        except ImportError:
            from scipy.io import wavfile
            data = (concatenated * 32767).astype(np.int16)
            wavfile.write(str(out_path), 24000, data)
        chattts_ok = True
    except (ConnectionAbortedError, ConnectionError, OSError) as e:
        err = str(e)
        if "10053" in err or "aborted" in err.lower():
            print("[TTS] 连接被中止，将尝试 edge-tts 回退")
        else:
            print(f"[TTS] ChatTTS 失败: {e}，将尝试 edge-tts 回退")
    except Exception as e:
        print(f"[TTS] ChatTTS 失败: {e}，将尝试 edge-tts 回退")

    if chattts_ok and out_path.exists():
        return str(out_path), None

    # 2) 回退到 edge-tts
    ok, err = _generate_tts_edge_tts(lines, str(out_path))
    if ok:
        return str(out_path), None
    return "", (err or "edge-tts 合成失败")


def mix_tts_with_music(tts_wav_path: str, music_path: str, output_path: str) -> bool:
    """
    使用 pydub 将 TTS 念白与背景音乐混音：念白为主，音乐压低并循环/截断到念白长度。
    """
    try:
        from pydub import AudioSegment

        tts = AudioSegment.from_wav(tts_wav_path)
        music = AudioSegment.from_file(music_path)
        # 统一为单声道、一致帧率（念白 24kHz，music 可能不同）
        tts = tts.set_channels(1).set_frame_rate(24000)
        music = music.set_channels(1).set_frame_rate(24000)
        # 音乐音量降低，避免盖过念白
        music = music - 12  # dB 降低
        len_tts = len(tts)
        # 音乐循环或截断到念白长度
        if len(music) < len_tts:
            music = music * (len_tts // len(music) + 1)
        music = music[:len_tts]
        # 叠加
        mixed = tts.overlay(music)
        mixed.export(output_path, format="wav")
        return True
    except Exception as e:
        print(f"[混音] 失败: {e}")
        return False


def run_performance_export(
    script: dict,
    output_dir: Path,
    session_id: str,
    music_file_path: str = None,
) -> dict:
    """
    执行阶段一导出：提取台词 → TTS → 若提供音乐则混音 → 返回音频 URL 相对路径。
    返回 {"success": bool, "audio_url": str 或 None, "error": str}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = _collect_lines_from_script(script)
    if not lines:
        return {"success": False, "audio_url": None, "error": "剧本中无台词，请先生成带台词的剧本"}

    tts_path, tts_error = generate_tts_audio(lines, output_dir, session_id)
    if not tts_path or not os.path.exists(tts_path):
        return {
            "success": False,
            "audio_url": None,
            "error": tts_error or "TTS 念白生成失败。若 ChatTTS 模型未下载成功，可换代理后重试；或安装 edge-tts（pip install edge-tts）并安装 ffmpeg 加入 PATH 以使用回退方案；或设置 CHATTTS_MODEL_DIR 指向已下载的 ChatTTS 模型目录。"
        }

    final_name = "performance.wav"
    final_path = output_dir / final_name

    # 优先使用上传的背景音乐；若无则尝试阶段二 MusicGen 生成戏曲伴奏
    music_to_use = music_file_path
    if not (music_to_use and os.path.exists(music_to_use)):
        try:
            from pydub import AudioSegment
            tts_segment = AudioSegment.from_wav(tts_path)
            tts_duration_sec = len(tts_segment) / 1000.0
            from src.pipeline.musicgen_background import generate_background_music
            musicgen_path = generate_background_music(tts_duration_sec, output_dir, session_id)
            if musicgen_path and os.path.exists(musicgen_path):
                music_to_use = musicgen_path
        except Exception as e:
            print(f"[演出导出] MusicGen 伴奏生成跳过: {e}")

    if music_to_use and os.path.exists(music_to_use):
        if mix_tts_with_music(tts_path, music_to_use, str(final_path)):
            return {"success": True, "audio_url": f"/api/performance_audio/{session_id}/performance.wav"}
        # 混音失败则退回仅念白
    import shutil
    try:
        shutil.copy(tts_path, final_path)
    except Exception:
        pass
    return {"success": True, "audio_url": f"/api/performance_audio/{session_id}/performance.wav"}
