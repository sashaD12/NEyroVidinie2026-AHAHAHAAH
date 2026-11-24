from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from .kinematics import compute_palm_axes, palm_center
from .landmarks import BONE_CONNECTIONS, FINGER_CHAINS, LANDMARK_INDEX, add, get_landmark, scale
from .types import CaptureResult, CapturedHand, Landmark

FINGER_COLORS: dict[str, tuple[int, int, int]] = {
    "thumb": (0, 140, 255),
    "index": (80, 220, 80),
    "middle": (255, 180, 60),
    "ring": (200, 80, 200),
    "pinky": (60, 60, 255),
}
PALM_COLOR = (230, 230, 230)
NORMAL_COLOR = (0, 255, 255)
TEXT_COLOR = (245, 245, 245)
SHADOW_COLOR = (20, 20, 20)

BONE_COLOR_BY_PAIR: dict[tuple[int, int], tuple[int, int, int]] = {}
for finger_name, chain in FINGER_CHAINS.items():
    color = FINGER_COLORS[finger_name]
    for index in range(len(chain) - 1):
        BONE_COLOR_BY_PAIR[(chain[index], chain[index + 1])] = color
    if finger_name != "thumb":
        BONE_COLOR_BY_PAIR[(0, chain[0])] = color
BONE_COLOR_BY_PAIR[(5, 9)] = PALM_COLOR
BONE_COLOR_BY_PAIR[(9, 13)] = PALM_COLOR
BONE_COLOR_BY_PAIR[(13, 17)] = PALM_COLOR


def _to_pixel(landmark: Landmark, width: int, height: int) -> tuple[int, int]:
    x_value = int(round(landmark.x * width))
    y_value = int(round(landmark.y * height))
    return x_value, y_value


def _put_text(
    frame: NDArray[np.uint8],
    text: str,
    origin: tuple[int, int],
    scale: float = 0.6,
) -> None:
    cv2.putText(
        frame,
        text,
        (origin[0] + 1, origin[1] + 1),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        SHADOW_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        TEXT_COLOR,
        1,
        cv2.LINE_AA,
    )


def _draw_hand(frame: NDArray[np.uint8], hand: CapturedHand, width: int, height: int) -> None:
    for start_index, end_index in BONE_CONNECTIONS:
        start = get_landmark(hand.landmarks, start_index)
        end = get_landmark(hand.landmarks, end_index)
        color = BONE_COLOR_BY_PAIR.get((start_index, end_index), PALM_COLOR)
        cv2.line(
            frame,
            _to_pixel(start, width, height),
            _to_pixel(end, width, height),
            color,
            2,
            cv2.LINE_AA,
        )
    for finger_name, chain in FINGER_CHAINS.items():
        color = FINGER_COLORS[finger_name]
        for landmark_index in chain:
            if landmark_index == 0:
                continue
            point = _to_pixel(get_landmark(hand.landmarks, landmark_index), width, height)
            radius = 5 if landmark_index in {4, 8, 12, 16, 20} else 3
            cv2.circle(frame, point, radius, color, -1, cv2.LINE_AA)
    wrist = _to_pixel(get_landmark(hand.landmarks, LANDMARK_INDEX["WRIST"]), width, height)
    cv2.circle(frame, wrist, 6, PALM_COLOR, -1, cv2.LINE_AA)
    _x_axis, _y_axis, palm_normal = compute_palm_axes(hand.landmarks, hand.handedness)
    center = palm_center(hand.landmarks)
    normal_tip = add(center, scale(palm_normal, 0.18))
    cv2.arrowedLine(
        frame,
        _to_pixel(Landmark(x=center.x, y=center.y, z=center.z), width, height),
        _to_pixel(Landmark(x=normal_tip.x, y=normal_tip.y, z=normal_tip.z), width, height),
        NORMAL_COLOR,
        2,
        cv2.LINE_AA,
        tipLength=0.25,
    )


def draw_capture(
    frame: NDArray[np.uint8],
    result: CaptureResult,
    fps: float,
) -> NDArray[np.uint8]:
    overlay = frame.copy()
    for hand in result.hands:
        _draw_hand(overlay, hand, result.frame_width, result.frame_height)
    _put_text(overlay, f"FPS  {fps:.1f}", (16, 32), 0.7)
    if len(result.hands) == 0:
        _put_text(overlay, "Hand: not detected", (16, 62), 0.65)
    else:
        y_value = 62
        for hand in result.hands:
            label = f"{hand.handedness}  {hand.confidence:.2f}"
            _put_text(overlay, label, (16, y_value), 0.65)
            y_value += 28
    _put_text(overlay, "Q  quit", (16, result.frame_height - 20), 0.55)
    return overlay
