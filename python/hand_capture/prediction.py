from __future__ import annotations

from .kinematics import compute_kinematics
from .landmarks import clone_landmark, clone_landmark_set
from .types import CaptureResult, CapturedHand, Handedness, Landmark


def _advance_landmarks(
    current: list[Landmark],
    previous: list[Landmark],
    sample_dt: float,
    ahead_dt: float,
) -> list[Landmark]:
    if sample_dt <= 1e-8 or ahead_dt <= 0.0:
        return clone_landmark_set(current)
    factor = min(ahead_dt, 0.08) / sample_dt
    advanced: list[Landmark] = []
    count = min(len(current), len(previous))
    for index in range(count):
        point = current[index]
        prev = previous[index]
        advanced.append(
            Landmark(
                x=point.x + (point.x - prev.x) * factor,
                y=point.y + (point.y - prev.y) * factor,
                z=point.z + (point.z - prev.z) * factor,
                visibility=point.visibility,
            )
        )
    while len(advanced) < len(current):
        advanced.append(clone_landmark(current[len(advanced)]))
    return advanced


def _hand_by_side(result: CaptureResult, handedness: Handedness) -> CapturedHand | None:
    for hand in result.hands:
        if hand.handedness == handedness:
            return hand
    return None


def extrapolate_result(
    current: CaptureResult,
    previous: CaptureResult | None,
    ahead_dt: float,
) -> CaptureResult:
    if previous is None or ahead_dt <= 1e-8:
        return current
    sample_dt = (current.timestamp_ms - previous.timestamp_ms) / 1000.0
    if sample_dt <= 1e-8:
        return current
    hands: list[CapturedHand] = []
    for hand in current.hands:
        prev_hand = _hand_by_side(previous, hand.handedness)
        if prev_hand is None:
            hands.append(hand)
            continue
        landmarks = _advance_landmarks(
            hand.landmarks,
            prev_hand.landmarks,
            sample_dt,
            ahead_dt,
        )
        world = _advance_landmarks(
            hand.world_landmarks,
            prev_hand.world_landmarks,
            sample_dt,
            ahead_dt,
        )
        canonical = _advance_landmarks(
            hand.canonical_landmarks,
            prev_hand.canonical_landmarks,
            sample_dt,
            ahead_dt,
        )
        hands.append(
            CapturedHand(
                handedness=hand.handedness,
                confidence=hand.confidence,
                landmarks=landmarks,
                world_landmarks=world,
                canonical_landmarks=canonical,
                kinematics=compute_kinematics(
                    world,
                    hand.handedness,
                    prev_hand.world_landmarks,
                    sample_dt,
                ),
                is_tracked=True,
            )
        )
    return CaptureResult(
        timestamp_ms=current.timestamp_ms + ahead_dt * 1000.0,
        frame_width=current.frame_width,
        frame_height=current.frame_height,
        hands=hands,
    )
