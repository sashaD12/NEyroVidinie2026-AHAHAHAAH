from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from .engine import BrushCommand, SketchCanvas

HINT = "S save   C clear   Q quit"
POSE_HINT = "Fist = lock   fist to point = arm   hold still = arm"


def _put(frame: NDArray[np.uint8], text: str, origin: tuple[int, int], scale: float = 0.58) -> None:
    cv2.putText(
        frame,
        text,
        (origin[0] + 1, origin[1] + 1),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (20, 20, 20),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (245, 245, 245),
        1,
        cv2.LINE_AA,
    )


def _draw_hue_bar(frame: NDArray[np.uint8], hue: float, origin_x: int, origin_y: int) -> None:
    height = 180
    width = 18
    for row in range(height):
        hue_value = int(round((row / max(height - 1, 1)) * 179.0))
        hsv = np.array([[[hue_value, 255, 255]]], dtype=np.uint8)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        color = (int(bgr[0]), int(bgr[1]), int(bgr[2]))
        cv2.line(
            frame,
            (origin_x, origin_y + row),
            (origin_x + width, origin_y + row),
            color,
            1,
        )
    marker_y = origin_y + int(round(hue * (height - 1)))
    cv2.rectangle(
        frame,
        (origin_x - 3, marker_y - 3),
        (origin_x + width + 3, marker_y + 3),
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )


def render_view(
    frame: NDArray[np.uint8],
    canvas: SketchCanvas,
    command: BrushCommand,
    status: str,
) -> NDArray[np.uint8]:
    view = canvas.composite(frame)
    if command.tip is not None:
        cursor_color = command.color
        if command.safety_state == "fuse":
            cursor_color = (40, 40, 220)
        elif command.safety_state in {"safe", "arming"}:
            cursor_color = (210, 210, 210)
        elif command.is_erasing:
            cursor_color = (40, 40, 40)
        cv2.circle(view, command.tip, command.thickness // 2 + 6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(view, command.tip, max(command.thickness // 2, 2), cursor_color, 2, cv2.LINE_AA)
    swatch_tl = (24, 20)
    swatch_br = (88, 84)
    cv2.rectangle(view, swatch_tl, swatch_br, command.color, -1, cv2.LINE_AA)
    cv2.rectangle(view, swatch_tl, swatch_br, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.circle(view, (120, 52), max(command.thickness // 2, 2), command.color, -1, cv2.LINE_AA)
    cv2.circle(view, (120, 52), max(command.thickness // 2, 2) + 4, (255, 255, 255), 1, cv2.LINE_AA)
    _draw_hue_bar(view, command.hue, 24, 100)
    mode = "SAFE"
    if command.safety_state == "arming":
        mode = "ARMING"
    elif command.safety_state == "fuse":
        mode = "FUSE"
    elif command.safety_state == "erase":
        mode = "ERASE"
    elif command.safety_state == "draw":
        mode = "DRAW"
    _put(view, mode, (16, 310), 0.8)
    if command.safety_state == "arming":
        bar_w = 120
        filled = int(round(command.arm_progress * bar_w))
        cv2.rectangle(view, (16, 322), (16 + bar_w, 334), (60, 60, 60), -1)
        cv2.rectangle(view, (16, 322), (16 + filled, 334), (80, 220, 80), -1)
    if status != "":
        _put(view, status, (16, 352), 0.55)
    _put(view, POSE_HINT, (16, view.shape[0] - 48), 0.52)
    _put(view, HINT, (16, view.shape[0] - 20), 0.52)
    return view
