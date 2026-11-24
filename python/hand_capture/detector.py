from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve

import numpy as np
from numpy.typing import NDArray

from .landmarks import ensure_landmark_count
from .types import Handedness, Landmark, RawHandDetection

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent / "models" / "hand_landmarker.task"


def ensure_model(model_path: Path = MODEL_PATH) -> Path:
    if model_path.exists() and model_path.stat().st_size > 1_000_000:
        return model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print("Скачиваю модель MediaPipe Hand Landmarker...")
    urlretrieve(MODEL_URL, model_path)
    return model_path


def _to_landmark(point: object) -> Landmark:
    x_value = float(getattr(point, "x"))
    y_value = float(getattr(point, "y"))
    z_value = float(getattr(point, "z"))
    visibility_raw = getattr(point, "visibility", None)
    visibility: float | None = None
    if visibility_raw is not None:
        visibility_value = float(visibility_raw)
        if visibility_value > 0.0:
            visibility = visibility_value
    return Landmark(x=x_value, y=y_value, z=z_value, visibility=visibility)


def _to_landmarks(points: object) -> list[Landmark]:
    landmarks: list[Landmark] = []
    if points is None:
        return landmarks
    for point in points:
        landmarks.append(_to_landmark(point))
    return ensure_landmark_count(landmarks)


def _read_handedness(categories: object, mirrored: bool) -> tuple[Handedness, float]:
    if not categories:
        return "Right", 0.0
    top = categories[0]
    name = str(getattr(top, "category_name", None) or getattr(top, "display_name", "Right"))
    score = float(getattr(top, "score", 0.0))
    handedness: Handedness = "Left" if name == "Left" else "Right"
    if mirrored:
        handedness = "Right" if handedness == "Left" else "Left"
    return handedness, score


class HandDetector:
    def __init__(
        self,
        max_hands: int,
        presence_threshold: float,
        model_path: Path | None = None,
    ) -> None:
        import mediapipe as mp

        resolved_model = ensure_model(model_path or MODEL_PATH)
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(resolved_model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=presence_threshold,
            min_hand_presence_confidence=presence_threshold,
            min_tracking_confidence=presence_threshold,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._mp = mp

    def detect(
        self,
        rgb_frame: NDArray[np.uint8],
        timestamp_ms: int,
        mirrored: bool,
    ) -> list[RawHandDetection]:
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(rgb_frame),
        )
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        detections: list[RawHandDetection] = []
        hand_landmarks = result.hand_landmarks or []
        world_landmarks = result.hand_world_landmarks or []
        handedness_lists = result.handedness or []
        for index, landmarks in enumerate(hand_landmarks):
            world = world_landmarks[index] if index < len(world_landmarks) else []
            categories = handedness_lists[index] if index < len(handedness_lists) else []
            handedness, score = _read_handedness(categories, mirrored)
            detections.append(
                RawHandDetection(
                    landmarks=_to_landmarks(landmarks),
                    world_landmarks=_to_landmarks(world),
                    handedness=handedness,
                    presence_score=score,
                )
            )
        return detections

    def close(self) -> None:
        closer = getattr(self._landmarker, "close", None)
        if closer is not None:
            closer()
