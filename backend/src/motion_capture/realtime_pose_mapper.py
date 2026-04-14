"""
Realtime pose mapper for webcam frames.

This module extracts body joints from a single frame with MediaPipe Pose,
then maps 3D-like body motion to 2D shadow-puppet controls.
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, Optional, Tuple

try:
    import cv2
except ImportError:  # pragma: no cover - handled by caller
    cv2 = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - handled by caller
    np = None

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - handled by caller
    mp = None


Point = Tuple[float, float, float]


def _clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def _segment_angle_deg(a: Point, b: Point) -> float:
    """Angle in degrees from point a -> b."""
    return float(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])))


class RealtimePoseMapper:
    """Frame-by-frame pose mapper used by /api/camera_pose_frame."""

    MP_ID = {
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28,
    }

    def __init__(
        self,
        model_complexity: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        smooth_alpha: float = 0.6,
    ):
        if cv2 is None or np is None:
            raise ImportError("opencv-python and numpy are required for realtime pose tracking.")
        if mp is None:
            raise ImportError("mediapipe is required for realtime pose tracking.")

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._smooth_alpha = float(_clamp(smooth_alpha, 0.05, 0.95))
        self._prev_values: Dict[str, float] = {}
        self._lock = Lock()

    def _smooth(self, key: str, value: float) -> float:
        old = self._prev_values.get(key, value)
        cur = old * (1.0 - self._smooth_alpha) + value * self._smooth_alpha
        self._prev_values[key] = cur
        return float(cur)

    def _landmark_to_point(self, lm) -> Point:
        return (float(lm.x), float(lm.y), float(lm.visibility))

    def process_bgr(self, frame_bgr: np.ndarray) -> Optional[Dict]:
        if cv2 is None or np is None:
            return None
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        with self._lock:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            result = self._pose.process(rgb)

        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks.landmark

        def p(name: str) -> Point:
            idx = self.MP_ID[name]
            return self._landmark_to_point(landmarks[idx])

        try:
            ls, rs = p("left_shoulder"), p("right_shoulder")
            le, re = p("left_elbow"), p("right_elbow")
            lw, rw = p("left_wrist"), p("right_wrist")
            lh, rh = p("left_hip"), p("right_hip")
            lk, rk = p("left_knee"), p("right_knee")
            la, ra = p("left_ankle"), p("right_ankle")
        except Exception:
            return None

        key_vis = [ls[2], rs[2], lw[2], rw[2], lh[2], rh[2], la[2], ra[2]]
        confidence = float(np.mean(key_vis))
        if confidence < 0.12:
            return None

        mid_sh = ((ls[0] + rs[0]) * 0.5, (ls[1] + rs[1]) * 0.5, confidence)
        mid_hip = ((lh[0] + rh[0]) * 0.5, (lh[1] + rh[1]) * 0.5, confidence)

        # Rotation baseline: segment down direction ~= 0 deg after subtracting 90.
        # Upper-arm angle is more stable/expressive than shoulder->wrist for puppets.
        left_arm_deg = _clamp(_segment_angle_deg(ls, le) - 90.0, -130.0, 130.0)
        right_arm_deg = _clamp(_segment_angle_deg(rs, re) - 90.0, -130.0, 130.0)
        left_leg_deg = _clamp(_segment_angle_deg(lh, la) - 90.0, -75.0, 75.0)
        right_leg_deg = _clamp(_segment_angle_deg(rh, ra) - 90.0, -75.0, 75.0)
        body_deg = _clamp(_segment_angle_deg(mid_hip, mid_sh) + 90.0, -35.0, 35.0)
        head_deg = _clamp(_segment_angle_deg(ls, rs), -45.0, 45.0)

        center_x = _clamp(mid_hip[0] * 100.0, 8.0, 92.0)
        center_y = _clamp(mid_hip[1] * 100.0 + 5.0, 12.0, 92.0)

        puppet_pose = {
            "confidence": confidence,
            "centerXPercent": self._smooth("centerXPercent", center_x),
            "centerYPercent": self._smooth("centerYPercent", center_y),
            "bodyRotateDeg": self._smooth("bodyRotateDeg", body_deg),
            "headRotateDeg": self._smooth("headRotateDeg", head_deg),
            "leftArmRotateDeg": self._smooth("leftArmRotateDeg", left_arm_deg),
            "rightArmRotateDeg": self._smooth("rightArmRotateDeg", right_arm_deg),
            "leftLegRotateDeg": self._smooth("leftLegRotateDeg", left_leg_deg),
            "rightLegRotateDeg": self._smooth("rightLegRotateDeg", right_leg_deg),
            "leftElbowRotateDeg": self._smooth("leftElbowRotateDeg", _clamp(_segment_angle_deg(le, lw) - 90.0, -130.0, 130.0)),
            "rightElbowRotateDeg": self._smooth("rightElbowRotateDeg", _clamp(_segment_angle_deg(re, rw) - 90.0, -130.0, 130.0)),
        }

        joints = {
            "left_shoulder": {"x": ls[0], "y": ls[1], "v": ls[2]},
            "right_shoulder": {"x": rs[0], "y": rs[1], "v": rs[2]},
            "left_elbow": {"x": le[0], "y": le[1], "v": le[2]},
            "right_elbow": {"x": re[0], "y": re[1], "v": re[2]},
            "left_wrist": {"x": lw[0], "y": lw[1], "v": lw[2]},
            "right_wrist": {"x": rw[0], "y": rw[1], "v": rw[2]},
            "left_hip": {"x": lh[0], "y": lh[1], "v": lh[2]},
            "right_hip": {"x": rh[0], "y": rh[1], "v": rh[2]},
            "left_knee": {"x": lk[0], "y": lk[1], "v": lk[2]},
            "right_knee": {"x": rk[0], "y": rk[1], "v": rk[2]},
            "left_ankle": {"x": la[0], "y": la[1], "v": la[2]},
            "right_ankle": {"x": ra[0], "y": ra[1], "v": ra[2]},
            "mid_shoulder": {"x": mid_sh[0], "y": mid_sh[1], "v": confidence},
            "mid_hip": {"x": mid_hip[0], "y": mid_hip[1], "v": confidence},
        }

        return {"joints": joints, "puppet_pose": puppet_pose}
