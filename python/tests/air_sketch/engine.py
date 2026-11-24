from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import cv2
import numpy as np
from numpy.typing import NDArray

from hand_capture.kinematics import palm_center
from hand_capture.landmarks import LANDMARK_INDEX, clamp, distance3, get_landmark
from hand_capture.types import CapturedHand, CaptureResult, Landmark

MIN_THICKNESS = 3
MAX_THICKNESS = 42
DEFAULT_COLOR = (255, 255, 255)
DEFAULT_THICKNESS = 10
DWELL_MS = 240.0
STILL_PX = 16.0
MAX_JUMP_PX = 96.0
MAX_SPEED_PX_S = 2400.0
RELEASE_MS = 110.0
FUSE_MS = 450.0


@dataclass
class BrushCommand:
    tip: tuple[int, int] | None
    is_drawing: bool
    is_erasing: bool
    is_fist: bool
    color: tuple[int, int, int]
    thickness: int
    hue: float
    has_palette: bool
    has_pen: bool
    safety_state: str
    arm_progress: float


def _to_pixel(landmark: Landmark, width: int, height: int) -> tuple[int, int]:
    x_value = int(round(clamp(landmark.x, 0.0, 1.0) * (width - 1)))
    y_value = int(round(clamp(landmark.y, 0.0, 1.0) * (height - 1)))
    return x_value, y_value


def _palm_size(landmarks: list[Landmark]) -> float:
    wrist = get_landmark(landmarks, LANDMARK_INDEX["WRIST"])
    middle = get_landmark(landmarks, LANDMARK_INDEX["MIDDLE_MCP"])
    size = distance3(wrist, middle)
    if size < 0.04:
        return 0.04
    return size


def _is_finger_up(landmarks: list[Landmark], tip_index: int, pip_index: int) -> bool:
    tip = get_landmark(landmarks, tip_index)
    pip = get_landmark(landmarks, pip_index)
    margin = _palm_size(landmarks) * 0.12
    return tip.y < pip.y - margin


def _finger_flags(hand: CapturedHand) -> tuple[bool, bool, bool, bool]:
    landmarks = hand.landmarks
    index_up = _is_finger_up(landmarks, LANDMARK_INDEX["INDEX_TIP"], LANDMARK_INDEX["INDEX_PIP"])
    middle_up = _is_finger_up(landmarks, LANDMARK_INDEX["MIDDLE_TIP"], LANDMARK_INDEX["MIDDLE_PIP"])
    ring_up = _is_finger_up(landmarks, LANDMARK_INDEX["RING_TIP"], LANDMARK_INDEX["RING_PIP"])
    pinky_up = _is_finger_up(landmarks, LANDMARK_INDEX["PINKY_TIP"], LANDMARK_INDEX["PINKY_PIP"])
    return index_up, middle_up, ring_up, pinky_up


def _is_pointing(hand: CapturedHand) -> bool:
    index_up, middle_up, ring_up, pinky_up = _finger_flags(hand)
    return index_up and (not middle_up) and (not ring_up) and (not pinky_up)


def _is_two_finger(hand: CapturedHand) -> bool:
    index_up, middle_up, ring_up, pinky_up = _finger_flags(hand)
    return index_up and middle_up and (not ring_up) and (not pinky_up)


def _is_fist(hand: CapturedHand) -> bool:
    index_up, middle_up, ring_up, pinky_up = _finger_flags(hand)
    return (not index_up) and (not middle_up) and (not ring_up) and (not pinky_up)


def _pick_roles(
    hands: list[CapturedHand],
) -> tuple[CapturedHand | None, CapturedHand | None]:
    if len(hands) == 0:
        return None, None
    if len(hands) == 1:
        return hands[0], None
    left: CapturedHand | None = None
    right: CapturedHand | None = None
    for hand in hands:
        if hand.handedness == "Left":
            left = hand
        else:
            right = hand
    if right is None:
        return left, None
    if left is None:
        return right, None
    return right, left


def _hue_to_bgr(hue: float) -> tuple[int, int, int]:
    hue_value = int(round(clamp(hue, 0.0, 1.0) * 179.0))
    hsv = np.array([[[hue_value, 255, 255]]], dtype=np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
    return int(bgr[0]), int(bgr[1]), int(bgr[2])


def _palette_from_hand(hand: CapturedHand) -> tuple[float, int]:
    landmarks = hand.landmarks
    center = palm_center(landmarks)
    hue = clamp(center.y, 0.0, 1.0)
    pinch = distance3(
        get_landmark(landmarks, LANDMARK_INDEX["THUMB_TIP"]),
        get_landmark(landmarks, LANDMARK_INDEX["INDEX_TIP"]),
    )
    ratio = clamp(pinch / (_palm_size(landmarks) * 1.6), 0.0, 1.0)
    thickness = int(round(MIN_THICKNESS + ratio * (MAX_THICKNESS - MIN_THICKNESS)))
    if thickness < MIN_THICKNESS:
        thickness = MIN_THICKNESS
    return hue, thickness


def command_from_result(
    result: CaptureResult,
    color: tuple[int, int, int],
    thickness: int,
    hue: float,
) -> BrushCommand:
    pen, palette = _pick_roles(result.hands)
    next_color = color
    next_thickness = thickness
    next_hue = hue
    has_palette = palette is not None
    if palette is not None:
        next_hue, next_thickness = _palette_from_hand(palette)
        next_color = _hue_to_bgr(next_hue)
    tip: tuple[int, int] | None = None
    is_drawing = False
    is_erasing = False
    is_fist = False
    if pen is not None:
        tip = _to_pixel(
            get_landmark(pen.landmarks, LANDMARK_INDEX["INDEX_TIP"]),
            result.frame_width,
            result.frame_height,
        )
        is_fist = _is_fist(pen)
        is_erasing = _is_two_finger(pen)
        is_drawing = _is_pointing(pen) or is_erasing
    return BrushCommand(
        tip=tip,
        is_drawing=is_drawing,
        is_erasing=is_erasing,
        is_fist=is_fist,
        color=next_color,
        thickness=next_thickness,
        hue=next_hue,
        has_palette=has_palette,
        has_pen=pen is not None,
        safety_state="safe",
        arm_progress=0.0,
    )


def _copy_command(
    command: BrushCommand,
    is_drawing: bool,
    safety_state: str,
    arm_progress: float,
) -> BrushCommand:
    return BrushCommand(
        tip=command.tip,
        is_drawing=is_drawing,
        is_erasing=command.is_erasing and is_drawing,
        is_fist=command.is_fist,
        color=command.color,
        thickness=command.thickness,
        hue=command.hue,
        has_palette=command.has_palette,
        has_pen=command.has_pen,
        safety_state=safety_state,
        arm_progress=arm_progress,
    )


def _distance_px(a: tuple[int, int], b: tuple[int, int]) -> float:
    return hypot(float(a[0] - b[0]), float(a[1] - b[1]))


class MotionSafety:
    def __init__(self) -> None:
        self._armed = False
        self._was_fist = False
        self._dwell_origin_ms: float | None = None
        self._still_anchor: tuple[int, int] | None = None
        self._last_tip: tuple[int, int] | None = None
        self._last_ms: float | None = None
        self._lost_ms: float | None = None
        self._fuse_until_ms = 0.0

    def _reset_dwell(self, tip: tuple[int, int] | None, timestamp_ms: float) -> None:
        self._dwell_origin_ms = timestamp_ms
        self._still_anchor = tip

    def _disarm(self) -> None:
        self._armed = False
        self._dwell_origin_ms = None
        self._still_anchor = None
        self._lost_ms = None

    def filter(self, command: BrushCommand, timestamp_ms: float) -> BrushCommand:
        if timestamp_ms < self._fuse_until_ms:
            self._armed = False
            self._last_tip = command.tip
            self._last_ms = timestamp_ms
            return _copy_command(command, False, "fuse", 0.0)
        if command.is_fist or command.tip is None or not command.has_pen:
            self._was_fist = command.is_fist
            self._disarm()
            self._last_tip = command.tip
            self._last_ms = timestamp_ms
            return _copy_command(command, False, "safe", 0.0)
        wants_ink = command.is_drawing
        if not wants_ink:
            if self._armed:
                if self._lost_ms is None:
                    self._lost_ms = timestamp_ms
                if timestamp_ms - self._lost_ms < RELEASE_MS:
                    self._last_tip = command.tip
                    self._last_ms = timestamp_ms
                    return _copy_command(command, False, "draw", 1.0)
            self._disarm()
            self._was_fist = False
            self._last_tip = command.tip
            self._last_ms = timestamp_ms
            return _copy_command(command, False, "safe", 0.0)
        self._lost_ms = None
        tip = command.tip
        if (not self._armed) and self._was_fist:
            self._armed = True
            self._was_fist = False
            self._dwell_origin_ms = None
            self._still_anchor = tip
            self._last_tip = None
        if not self._armed:
            if self._dwell_origin_ms is None or self._still_anchor is None:
                self._reset_dwell(tip, timestamp_ms)
            elif _distance_px(tip, self._still_anchor) > STILL_PX:
                self._reset_dwell(tip, timestamp_ms)
            origin = self._dwell_origin_ms
            if origin is None:
                origin = timestamp_ms
            elapsed = timestamp_ms - origin
            progress = clamp(elapsed / DWELL_MS, 0.0, 1.0)
            if elapsed < DWELL_MS:
                self._last_tip = tip
                self._last_ms = timestamp_ms
                return _copy_command(command, False, "arming", progress)
            self._armed = True
        tripped = False
        if self._last_tip is not None:
            travel = _distance_px(tip, self._last_tip)
            if travel > MAX_JUMP_PX:
                tripped = True
            dt_s = 0.0
            if self._last_ms is not None:
                dt_s = max((timestamp_ms - self._last_ms) / 1000.0, 0.0)
            if dt_s > 1e-4 and (travel / dt_s) > MAX_SPEED_PX_S:
                tripped = True
        self._last_tip = tip
        self._last_ms = timestamp_ms
        if tripped:
            self._disarm()
            self._fuse_until_ms = timestamp_ms + FUSE_MS
            return _copy_command(command, False, "fuse", 0.0)
        state = "erase" if command.is_erasing else "draw"
        return _copy_command(command, True, state, 1.0)


class SketchCanvas:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.bgr: NDArray[np.uint8] = np.zeros((height, width, 3), dtype=np.uint8)
        self.alpha: NDArray[np.uint8] = np.zeros((height, width), dtype=np.uint8)
        self.last_tip: tuple[int, int] | None = None
        self.color: tuple[int, int, int] = DEFAULT_COLOR
        self.thickness: int = DEFAULT_THICKNESS
        self.hue: float = 0.0

    def resize(self, width: int, height: int) -> None:
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self.bgr = np.zeros((height, width, 3), dtype=np.uint8)
        self.alpha = np.zeros((height, width), dtype=np.uint8)
        self.last_tip = None

    def clear(self) -> None:
        self.bgr[:] = 0
        self.alpha[:] = 0
        self.last_tip = None

    def apply(self, command: BrushCommand) -> None:
        self.color = command.color
        self.thickness = command.thickness
        self.hue = command.hue
        if (not command.is_drawing) or command.tip is None:
            self.last_tip = None
            return
        end = command.tip
        start = self.last_tip if self.last_tip is not None else end
        stamp = command.thickness
        if stamp % 2 == 0:
            stamp += 1
        radius = max(stamp // 2, 1)
        if command.is_erasing:
            cv2.line(self.bgr, start, end, (0, 0, 0), stamp, cv2.LINE_AA)
            cv2.circle(self.bgr, end, radius, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.line(self.alpha, start, end, 0, stamp, cv2.LINE_AA)
            cv2.circle(self.alpha, end, radius, 0, -1, cv2.LINE_AA)
        else:
            cv2.line(self.bgr, start, end, command.color, stamp, cv2.LINE_AA)
            cv2.circle(self.bgr, end, radius, command.color, -1, cv2.LINE_AA)
            cv2.line(self.alpha, start, end, 255, stamp, cv2.LINE_AA)
            cv2.circle(self.alpha, end, radius, 255, -1, cv2.LINE_AA)
        self.last_tip = end

    def composite(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        alpha = self.alpha.astype(np.float32) / 255.0
        alpha_3 = alpha[:, :, None]
        blended = frame.astype(np.float32) * (1.0 - alpha_3) + self.bgr.astype(np.float32) * alpha_3
        return blended.astype(np.uint8)

    def to_png_bgra(self) -> NDArray[np.uint8]:
        b_channel, g_channel, r_channel = cv2.split(self.bgr)
        return cv2.merge((b_channel, g_channel, r_channel, self.alpha))

    def save_png(self, path: str) -> None:
        cv2.imwrite(path, self.to_png_bgra())
