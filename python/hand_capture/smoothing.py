from __future__ import annotations

import math

from .landmarks import LANDMARK_COUNT, clone_landmark
from .types import (
    CaptureSmoothing,
    Landmark,
    LandmarkFilterState,
    OneEuroFilterState,
)


def create_one_euro_state() -> OneEuroFilterState:
    return OneEuroFilterState(is_initialized=False, x_prev=0.0, dx_prev=0.0)


def create_landmark_filter_state() -> LandmarkFilterState:
    return LandmarkFilterState(
        x=create_one_euro_state(),
        y=create_one_euro_state(),
        z=create_one_euro_state(),
    )


def create_filter_list() -> list[LandmarkFilterState]:
    filters: list[LandmarkFilterState] = []
    for _index in range(LANDMARK_COUNT):
        filters.append(create_landmark_filter_state())
    return filters


def smoothing_factor(time_delta: float, cutoff: float) -> float:
    radius = 2.0 * math.pi * cutoff * time_delta
    return radius / (radius + 1.0)


def exponential_smoothing(alpha: float, value: float, previous: float) -> float:
    return alpha * value + (1.0 - alpha) * previous


def filter_scalar(
    state: OneEuroFilterState,
    value: float,
    time_delta: float,
    smoothing: CaptureSmoothing,
) -> tuple[OneEuroFilterState, float]:
    if time_delta <= 1e-8:
        if not state.is_initialized:
            return OneEuroFilterState(True, value, 0.0), value
        return state, state.x_prev
    if not state.is_initialized:
        return OneEuroFilterState(True, value, 0.0), value
    dx = (value - state.x_prev) / time_delta
    edx = exponential_smoothing(
        smoothing_factor(time_delta, smoothing.d_cutoff),
        dx,
        state.dx_prev,
    )
    cutoff = smoothing.min_cutoff + smoothing.beta * abs(edx)
    filtered = exponential_smoothing(
        smoothing_factor(time_delta, cutoff),
        value,
        state.x_prev,
    )
    return OneEuroFilterState(True, filtered, edx), filtered


def filter_landmark(
    state: LandmarkFilterState,
    landmark: Landmark,
    time_delta: float,
    smoothing: CaptureSmoothing,
) -> tuple[LandmarkFilterState, Landmark]:
    x_state, x_value = filter_scalar(state.x, landmark.x, time_delta, smoothing)
    y_state, y_value = filter_scalar(state.y, landmark.y, time_delta, smoothing)
    z_state, z_value = filter_scalar(state.z, landmark.z, time_delta, smoothing)
    filtered = Landmark(
        x=x_value,
        y=y_value,
        z=z_value,
        visibility=landmark.visibility,
    )
    return LandmarkFilterState(x=x_state, y=y_state, z=z_state), filtered


def filter_landmark_set(
    filters: list[LandmarkFilterState],
    landmarks: list[Landmark],
    time_delta: float,
    smoothing: CaptureSmoothing,
) -> tuple[list[LandmarkFilterState], list[Landmark]]:
    next_filters: list[LandmarkFilterState] = []
    filtered_landmarks: list[Landmark] = []
    count = min(LANDMARK_COUNT, len(filters), len(landmarks))
    for index in range(count):
        next_state, filtered = filter_landmark(
            filters[index],
            landmarks[index],
            time_delta,
            smoothing,
        )
        next_filters.append(next_state)
        filtered_landmarks.append(filtered)
    while len(next_filters) < LANDMARK_COUNT:
        next_filters.append(create_landmark_filter_state())
    while len(filtered_landmarks) < LANDMARK_COUNT:
        filtered_landmarks.append(Landmark(x=0.0, y=0.0, z=0.0))
    return next_filters, filtered_landmarks


def passthrough_landmarks(landmarks: list[Landmark]) -> list[Landmark]:
    cloned: list[Landmark] = []
    for landmark in landmarks:
        cloned.append(clone_landmark(landmark))
    return cloned
