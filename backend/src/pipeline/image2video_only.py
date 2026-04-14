"""
图生视频导出流水线（简化版）：
- 不再生成念白 + 背景音乐，而是将舞台截图/用户上传图片 + 剧本台词 + 动作/情绪
  发送到外部「图生视频」大模型服务，由其直接返回带演唱的视频。

集成方式：
- 通过环境变量 IMAGE2VIDEO_API_URL 配置外部服务地址（HTTP POST）。
- 若未配置或调用失败，则返回错误信息，前端可提示用户检查配置。
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any

import requests


def _collect_lines_from_script(script: Dict[str, Any]) -> List[str]:
  """从剧本中按场景顺序收集所有台词句子，用于传给图生视频模型。"""
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


def run_image2video_only(
  script: Dict[str, Any],
  output_dir: Path,
  session_id: str,
  frame_image_path: str,
  action_sequence: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
  """
  使用外部图生视频 API 直接生成 MP4。

  约定（可根据实际服务稍后调整）：
  - 环境变量 IMAGE2VIDEO_API_URL: 接口地址，例如 https://your-api.example.com/image2video
  - 请求方式: POST multipart/form-data
    * files['image']: 场景图 PNG/JPG
    * data['script']: 台词文本（多句用换行拼接）
    * data['actions']: JSON 字符串，来自前端的动作/情绪序列（可选）
  - 响应: 若 status_code==200，返回视频二进制内容（Content-Type: video/mp4 或 application/octet-stream）
  """
  api_url = os.environ.get("IMAGE2VIDEO_API_URL", "").strip()
  if not api_url:
    return {
      "success": False,
      "video_url": None,
      "error": "未配置 IMAGE2VIDEO_API_URL 环境变量，请在后端配置图生视频服务地址后再试。",
    }

  if not frame_image_path or not os.path.exists(frame_image_path):
    return {
      "success": False,
      "video_url": None,
      "error": "缺少场景图片，请先在导出站上传一张截图。",
    }

  lines = _collect_lines_from_script(script)
  if not lines:
    return {
      "success": False,
      "video_url": None,
      "error": "剧本中无台词，请先生成带台词的剧本。",
    }

  output_dir = Path(output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)
  video_path = output_dir / "performance_image2video.mp4"

  payload = {
    "script": "\n".join(lines),
  }
  if action_sequence:
    try:
      payload["actions"] = json.dumps(action_sequence, ensure_ascii=False)
    except TypeError:
      # 动作序列无法序列化时直接忽略
      pass

  files = {
    "image": (os.path.basename(frame_image_path), open(frame_image_path, "rb"), "image/png"),
  }

  try:
    timeout = int(os.environ.get("IMAGE2VIDEO_TIMEOUT", "600"))
  except ValueError:
    timeout = 600

  try:
    resp = requests.post(api_url, data=payload, files=files, timeout=timeout)
  except Exception as e:
    return {
      "success": False,
      "video_url": None,
      "error": f"调用图生视频服务失败：{e}",
    }

  if resp.status_code != 200:
    # 优先解析 JSON 错误信息
    err_msg = ""
    try:
      data = resp.json()
      err_msg = data.get("message") or data.get("error") or ""
    except Exception:
      pass
    if not err_msg:
      err_msg = f"图生视频服务返回状态码 {resp.status_code}"
    return {"success": False, "video_url": None, "error": err_msg}

  try:
    with open(video_path, "wb") as f:
      f.write(resp.content)
  except Exception as e:
    return {
      "success": False,
      "video_url": None,
      "error": f"保存图生视频结果失败：{e}",
    }

  if not video_path.exists():
    return {
      "success": False,
      "video_url": None,
      "error": "图生视频服务未返回有效视频文件。",
    }

  # 统一复用 /api/performance_audio/<session_id>/<filename> 的静态访问方式
  rel_url = f"/api/performance_audio/{session_id}/{video_path.name}"
  return {"success": True, "video_url": rel_url, "error": None}

