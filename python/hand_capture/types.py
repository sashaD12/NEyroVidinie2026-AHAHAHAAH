from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Handedness = Literal["Left", "Right"]


@dataclass
class Vec3:
    x: float
    y: float
    z: float


@dataclass
class Landmark(Vec3):
    visibility: float | None = None


@dataclass
class RawHandDetection:
    landmarks: list[Landmark]
    world_landmarks: list[Landmark]
    handedness: Handedness
    presence_score: float


@dataclass
class FingerAngles:
    mcp: float
    pip: float
    dip: float


@dataclass
class FingertipVelocities:
    thumb: Vec3
    index: Vec3
    middle: Vec3
    ring: Vec3
    pinky: Vec3


@dataclass
class HandFingerAngles:
    thumb: FingerAngles
    index: FingerAngles
    middle: FingerAngles
    ring: FingerAngles
    pinky: FingerAngles


@dataclass
class HandKinematics:
    palm_normal: Vec3
    palm_direction: Vec3
    finger_angles: HandFingerAngles
    wrist_velocity: Vec3
    fingertip_velocities: FingertipVelocities


@dataclass
class CapturedHand:
    handedness: Handedness
    confidence: float
    landmarks: list[Landmark]
    world_landmarks: list[Landmark]
    canonical_landmarks: list[Landmark]
    kinematics: HandKinematics
    is_tracked: bool


@dataclass
class CaptureResult:
    timestamp_ms: float
    frame_width: int
    frame_height: int
    hands: list[CapturedHand]


@dataclass
class CaptureSmoothing:
    min_cutoff: float
    beta: float
    d_cutoff: float


@dataclass
class CaptureConfig:
    presence_threshold: float
    max_hands: int
    smoothing: CaptureSmoothing
    enable_canonical_frame: bool
    enable_smoothing: bool


@dataclass
class OneEuroFilterState:
    is_initialized: bool
    x_prev: float
    dx_prev: float


@dataclass
class LandmarkFilterState:
    x: OneEuroFilterState
    y: OneEuroFilterState
    z: OneEuroFilterState


@dataclass
class HandFilterBank:
    image: list[LandmarkFilterState]
    world: list[LandmarkFilterState]


@dataclass
class CaptureState:
    previous_timestamp_ms: float | None
    filters_by_hand: dict[Handedness, HandFilterBank] = field(default_factory=dict)
    previous_canonical_by_hand: dict[Handedness, list[Landmark]] = field(default_factory=dict)
    previous_smoothed_by_hand: dict[Handedness, list[Landmark]] = field(default_factory=dict)


def default_capture_config() -> CaptureConfig:
    return CaptureConfig(
        presence_threshold=0.5,
        max_hands=2,
        smoothing=CaptureSmoothing(min_cutoff=1.0, beta=0.007, d_cutoff=1.0),
        enable_canonical_frame=True,
        enable_smoothing=True,
    )
