from __future__ import annotations

from .kinematics import compute_canonical_landmarks, compute_kinematics
from .landmarks import clone_landmark_set, ensure_landmark_count
from .smoothing import create_filter_list, filter_landmark_set, passthrough_landmarks
from .types import (
    CaptureConfig,
    CaptureResult,
    CaptureState,
    CapturedHand,
    HandFilterBank,
    Handedness,
    RawHandDetection,
)


class HandCapture:
    def __init__(self, config: CaptureConfig) -> None:
        self.config = config
        self.state = CaptureState(previous_timestamp_ms=None)

    def process(
        self,
        detections: list[RawHandDetection],
        timestamp_ms: float,
        frame_width: int,
        frame_height: int,
    ) -> CaptureResult:
        dt_seconds = 0.0
        if self.state.previous_timestamp_ms is not None:
            dt_seconds = (timestamp_ms - self.state.previous_timestamp_ms) / 1000.0
            if dt_seconds < 0.0:
                dt_seconds = 0.0
        selected = self._select_detections(detections)
        captured: list[CapturedHand] = []
        seen: set[Handedness] = set()
        for detection in selected:
            captured.append(self._process_hand(detection, dt_seconds))
            seen.add(detection.handedness)
        self.state.previous_timestamp_ms = timestamp_ms
        return CaptureResult(
            timestamp_ms=timestamp_ms,
            frame_width=frame_width,
            frame_height=frame_height,
            hands=captured,
        )

    def _select_detections(
        self,
        detections: list[RawHandDetection],
    ) -> list[RawHandDetection]:
        best_by_hand: dict[Handedness, RawHandDetection] = {}
        for detection in detections:
            if detection.presence_score < self.config.presence_threshold:
                continue
            current = best_by_hand.get(detection.handedness)
            if current is None or detection.presence_score > current.presence_score:
                best_by_hand[detection.handedness] = detection
        selected = list(best_by_hand.values())
        selected.sort(key=lambda item: item.presence_score, reverse=True)
        return selected[: self.config.max_hands]

    def _process_hand(self, detection: RawHandDetection, dt_seconds: float) -> CapturedHand:
        image_landmarks = ensure_landmark_count(detection.landmarks)
        if len(detection.world_landmarks) > 0:
            world_landmarks = ensure_landmark_count(detection.world_landmarks)
        else:
            world_landmarks = clone_landmark_set(image_landmarks)
        bank = self.state.filters_by_hand.get(detection.handedness)
        if bank is None:
            bank = HandFilterBank(image=create_filter_list(), world=create_filter_list())
        if self.config.enable_smoothing:
            image_filters, smoothed_image = filter_landmark_set(
                bank.image,
                image_landmarks,
                dt_seconds,
                self.config.smoothing,
            )
            world_filters, smoothed_world = filter_landmark_set(
                bank.world,
                world_landmarks,
                dt_seconds,
                self.config.smoothing,
            )
            bank = HandFilterBank(image=image_filters, world=world_filters)
        else:
            smoothed_image = passthrough_landmarks(image_landmarks)
            smoothed_world = passthrough_landmarks(world_landmarks)
        self.state.filters_by_hand[detection.handedness] = bank
        if self.config.enable_canonical_frame:
            canonical = compute_canonical_landmarks(smoothed_world, detection.handedness)
        else:
            canonical = clone_landmark_set(smoothed_image)
        previous = self.state.previous_smoothed_by_hand.get(detection.handedness)
        kinematics = compute_kinematics(
            smoothed_world,
            detection.handedness,
            previous,
            dt_seconds,
        )
        self.state.previous_smoothed_by_hand[detection.handedness] = clone_landmark_set(
            smoothed_world
        )
        self.state.previous_canonical_by_hand[detection.handedness] = clone_landmark_set(
            canonical
        )
        return CapturedHand(
            handedness=detection.handedness,
            confidence=detection.presence_score,
            landmarks=smoothed_image,
            world_landmarks=smoothed_world,
            canonical_landmarks=canonical,
            kinematics=kinematics,
            is_tracked=True,
        )
