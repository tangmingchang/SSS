"""
通义万相（阿里云 DashScope）图生视频简化版：
- 使用 I2V 接口：图片 + 文本 prompt 生成视频（可自动配音）。
- 直接在皮影后端同步调用：创建任务 → 轮询任务状态 → 下载视频到本地。

环境变量：
- DASHSCOPE_API_KEY: 阿里云百炼 API Key（必填）
- DASHSCOPE_BASE_URL: 可选，默认 "https://dashscope.aliyuncs.com/api/v1"
- WANX_I2V_MODEL: 可选，默认 "wan2.5-i2v-preview"
- WANX_I2V_RESOLUTION: 可选，默认 "720P"（480P/720P/1080P）
- WANX_I2V_DURATION: 可选，默认 "5"（秒，需符合模型支持）
- WANX_I2V_POLL_TIMEOUT: 可选，总等待时长（秒），默认 600
- WANX_I2V_POLL_INTERVAL: 可选，轮询间隔（秒），默认 8
"""

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


def _collect_lines_from_script(script: Dict[str, Any]) -> List[str]:
    """从剧本中按场景顺序收集所有台词句子。"""
    if not script or not isinstance(script, dict):
        return []
    scenes = script.get("scenes") or []
    lines: List[str] = []
    for s in sorted(scenes, key=lambda x: x.get("scene_number", 0)):
        for line in (s.get("lines") or []):
            if isinstance(line, str):
                text = line.strip()
                if text:
                    lines.append(text)
    return lines


def _build_prompt(script: Dict[str, Any], action_sequence: Optional[List[Dict[str, Any]]]) -> str:
    """组合台词 + 动作/情绪，生成给通义万相的视频提示词。

    重点强调（尽量简洁直接，避免太多说明淹没歌词）：
    - 必须有清晰的人声演唱，而不是只有伴奏或环境声；
    - 要逐句朗读/演唱下面给出的中文台词，并且对口型；
    - 背景音乐为皮影戏/戏曲风格，与情绪同步，但人声是绝对主角。
    """
    lines = _collect_lines_from_script(script)
    script_text = "\n".join(lines) if lines else ""

    if not script_text:
        base = (
            "请生成一段中国传统皮影戏风格的演出视频。"
            "画面中有皮影角色在舞台上表演，并配有符合情绪变化的戏曲伴奏音乐。"
        )
    else:
        base = (
            "生成一段中国传统皮影戏风格的【有声】演出视频。\n"
            "要求非常明确：\n"
            "1）一定要有清晰的中文人声朗读/演唱，不要只生成纯音乐或环境音；\n"
            "2）人声要逐句朗读/演唱下面给出的中文台词，每一行都要读出来，并与口型和表演同步；\n"
            "3）画面是皮影戏舞台，角色按歌词情绪做表演；\n"
            "4）背景音乐为中国戏曲/皮影戏伴奏，烘托气氛，但人声音量要清晰可辨，是主角；\n\n"
            "下面是【必须逐句朗读/演唱】的中文台词（每一行是一句，按顺序读完）：\n"
            f"{script_text}\n"
        )

    if action_sequence:
        try:
            actions_json = json.dumps(action_sequence, ensure_ascii=False, indent=2)
        except TypeError:
            actions_json = ""
        if actions_json:
            base += (
                "\n下面是该段演出对应的动作和情绪时间线，可据此设计角色的表演动作、"
                "情绪变化以及镜头运动，使之与歌词、人声和音乐的节奏相协调：\n"
                f"{actions_json}\n"
            )

    base += "\n请输出横屏 16:9 高清视频，务必包含清晰的人声朗读/演唱和与之匹配的皮影戏风格背景音乐。"
    return base


def _resolution_to_size(resolution: str) -> str:
    """将分辨率字符串转换为万相 API 需要的 size 参数。"""
    mapping = {
        "480P": "832*480",
        "720P": "1280*720",
        "1080P": "1920*1080",
    }
    return mapping.get(resolution.upper(), "1280*720")


def _image_path_to_data_uri(path: Path) -> str:
    """将本地图片文件转换为 data URI（base64），用于 img_url 字段。"""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"图片文件不存在: {path}")
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    ext = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


def run_wanx_image2video(
    script: Dict[str, Any],
    output_dir: Path,
    session_id: str,
    frame_image_path: str,
    action_sequence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    使用通义万相图生视频接口生成带音频的视频。

    返回：
        {"success": True, "video_url": 相对URL, "error": None}
        或 {"success": False, "video_url": None, "error": 错误信息}
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "video_url": None,
            "error": "未配置 DASHSCOPE_API_KEY，无法调用通义万相图生视频接口。",
        }

    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1").strip().rstrip("/")
    model_name = os.environ.get("WANX_I2V_MODEL", "wan2.5-i2v-preview").strip()
    resolution = os.environ.get("WANX_I2V_RESOLUTION", "720P").strip() or "720P"
    try:
        duration = int(os.environ.get("WANX_I2V_DURATION", "5"))
    except ValueError:
        duration = 5

    try:
        poll_timeout = int(os.environ.get("WANX_I2V_POLL_TIMEOUT", "600"))
    except ValueError:
        poll_timeout = 600
    try:
        poll_interval = int(os.environ.get("WANX_I2V_POLL_INTERVAL", "8"))
    except ValueError:
        poll_interval = 8

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_path = Path(frame_image_path)
    if not frame_path.is_file():
        return {
            "success": False,
            "video_url": None,
            "error": f"缺少场景图片: {frame_image_path}",
        }

    try:
        img_url = _image_path_to_data_uri(frame_path)
    except Exception as e:
        return {
            "success": False,
            "video_url": None,
            "error": f"读取场景图片失败: {e}",
        }

    prompt = _build_prompt(script, action_sequence)
    size = _resolution_to_size(resolution)

    create_url = f"{base_url}/services/aigc/video-generation/video-synthesis"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-DashScope-Async": "enable",
        "Content-Type": "application/json",
    }
    body = {
        "model": model_name,
        "input": {
            "img_url": img_url,
            "prompt": prompt,
        },
        "parameters": {
            "size": size,
            "duration": duration,
            "prompt_extend": True,
            "audio": True,  # 使用模型自带配音
        },
    }

    try:
        resp = requests.post(create_url, headers=headers, json=body, timeout=60)
    except Exception as e:
        return {
            "success": False,
            "video_url": None,
            "error": f"创建通义万相视频任务失败: {e}",
        }

    if resp.status_code != 200:
        try:
            data = resp.json()
            msg = data.get("message") or data.get("error") or resp.text
        except Exception:
            msg = resp.text
        return {
            "success": False,
            "video_url": None,
            "error": f"创建通义万相任务失败: HTTP {resp.status_code}: {msg}",
        }

    data = resp.json()
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        return {
            "success": False,
            "video_url": None,
            "error": f"未从通义万相响应中获得 task_id: {data}",
        }

    # 轮询任务状态
    task_url = f"{base_url}/tasks/{task_id}"
    start = time.time()
    last_status = ""
    video_url_remote = ""

    while time.time() - start < poll_timeout:
        try:
            r = requests.get(task_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        except Exception as e:
            return {
                "success": False,
                "video_url": None,
                "error": f"查询通义万相任务状态失败: {e}",
            }

        if r.status_code != 200:
            try:
                err_data = r.json()
                msg = err_data.get("message") or r.text
            except Exception:
                msg = r.text
            return {
                "success": False,
                "video_url": None,
                "error": f"查询任务失败: HTTP {r.status_code}: {msg}",
            }

        result = r.json()
        output = result.get("output") or {}
        status = output.get("task_status") or output.get("status") or ""
        last_status = status

        if status == "SUCCEEDED":
            video_url_remote = output.get("video_url") or ""
            break
        if status in {"FAILED", "ERROR"}:
            msg = output.get("message") or "通义万相任务执行失败"
            return {
                "success": False,
                "video_url": None,
                "error": msg,
            }
        time.sleep(poll_interval)

    if not video_url_remote:
        return {
            "success": False,
            "video_url": None,
            "error": f"等待通义万相任务完成超时，最后状态: {last_status or '未知'}",
        }

    # 下载视频到本地
    try:
        r = requests.get(video_url_remote, timeout=600)
        if r.status_code != 200:
            return {
                "success": False,
                "video_url": None,
                "error": f"下载视频失败: HTTP {r.status_code}",
            }
        filename = f"wanx_{session_id}.mp4"
        local_path = output_dir / filename
        local_path.write_bytes(r.content)
    except Exception as e:
        return {
            "success": False,
            "video_url": None,
            "error": f"保存通义万相视频失败: {e}",
        }

    rel_url = f"/api/performance_audio/{session_id}/{filename}"
    return {
        "success": True,
        "video_url": rel_url,
        "error": None,
    }

