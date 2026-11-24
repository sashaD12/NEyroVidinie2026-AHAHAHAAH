from __future__ import annotations

import math

from .landmarks import (
    FINGER_JOINTS,
    FINGERTIP_INDEX,
    LANDMARK_INDEX,
    add,
    clamp,
    cross,
    distance3,
    dot,
    get_landmark,
    normalize,
    scale,
    subtract,
    zero_vec3,
)
from .types import (
    FingerAngles,
    FingertipVelocities,
    HandFingerAngles,
    HandKinematics,
    Handedness,
    Landmark,
    Vec3,
)


def joint_angle(a: Vec3, b: Vec3, c: Vec3) -> float:
    ba = normalize(subtract(a, b))
    bc = normalize(subtract(c, b))
    cosine = clamp(dot(ba, bc), -1.0, 1.0)
    return math.acos(cosine)


def compute_finger_angles(landmarks: list[Landmark]) -> HandFingerAngles:
    angles: dict[str, FingerAngles] = {}
    for finger_name, joints in FINGER_JOINTS.items():
        mcp_points = joints["mcp"]
        pip_points = joints["pip"]
        dip_points = joints["dip"]
        angles[finger_name] = FingerAngles(
            mcp=joint_angle(
                get_landmark(landmarks, mcp_points[0]),
                get_landmark(landmarks, mcp_points[1]),
                get_landmark(landmarks, mcp_points[2]),
            ),
            pip=joint_angle(
                get_landmark(landmarks, pip_points[0]),
                get_landmark(landmarks, pip_points[1]),
                get_landmark(landmarks, pip_points[2]),
            ),
            dip=joint_angle(
                get_landmark(landmarks, dip_points[0]),
                get_landmark(landmarks, dip_points[1]),
                get_landmark(landmarks, dip_points[2]),
            ),
        )
    return HandFingerAngles(
        thumb=angles["thumb"],
        index=angles["index"],
        middle=angles["middle"],
        ring=angles["ring"],
        pinky=angles["pinky"],
    )


def compute_palm_axes(landmarks: list[Landmark], handedness: Handedness) -> tuple[Vec3, Vec3, Vec3]:
    wrist = get_landmark(landmarks, LANDMARK_INDEX["WRIST"])
    index_mcp = get_landmark(landmarks, LANDMARK_INDEX["INDEX_MCP"])
    pinky_mcp = get_landmark(landmarks, LANDMARK_INDEX["PINKY_MCP"])
    middle_mcp = get_landmark(landmarks, LANDMARK_INDEX["MIDDLE_MCP"])
    palm_direction = normalize(subtract(middle_mcp, wrist))
    across = subtract(index_mcp, pinky_mcp)
    if handedness == "Left":
        across = scale(across, -1.0)
    x_axis = normalize(across)
    z_axis = normalize(cross(x_axis, palm_direction))
    x_axis = normalize(cross(palm_direction, z_axis))
    return x_axis, palm_direction, z_axis


def compute_canonical_landmarks(
    landmarks: list[Landmark],
    handedness: Handedness,
) -> list[Landmark]:
    wrist = get_landmark(landmarks, LANDMARK_INDEX["WRIST"])
    middle_mcp = get_landmark(landmarks, LANDMARK_INDEX["MIDDLE_MCP"])
    palm_size = distance3(wrist, middle_mcp)
    if palm_size <= 1e-8:
        palm_size = 1.0
    x_axis, y_axis, z_axis = compute_palm_axes(landmarks, handedness)
    canonical: list[Landmark] = []
    for landmark in landmarks:
        delta = subtract(landmark, wrist)
        point = Landmark(
            x=dot(delta, x_axis) / palm_size,
            y=dot(delta, y_axis) / palm_size,
            z=dot(delta, z_axis) / palm_size,
            visibility=landmark.visibility,
        )
        canonical.append(point)
    return canonical


def velocity_between(current: Vec3, previous: Vec3, dt_seconds: float) -> Vec3:
    if dt_seconds <= 1e-8:
        return zero_vec3()
    return scale(subtract(current, previous), 1.0 / dt_seconds)


def compute_fingertip_velocities(
    current: list[Landmark],
    previous: list[Landmark] | None,
    dt_seconds: float,
) -> FingertipVelocities:
    if previous is None:
        return FingertipVelocities(
            thumb=zero_vec3(),
            index=zero_vec3(),
            middle=zero_vec3(),
            ring=zero_vec3(),
            pinky=zero_vec3(),
        )
    components: dict[str, Vec3] = {}
    for finger_name, index in FINGERTIP_INDEX.items():
        components[finger_name] = velocity_between(
            get_landmark(current, index),
            get_landmark(previous, index),
            dt_seconds,
        )
    return FingertipVelocities(
        thumb=components["thumb"],
        index=components["index"],
        middle=components["middle"],
        ring=components["ring"],
        pinky=components["pinky"],
    )


def compute_kinematics(
    landmarks: list[Landmark],
    handedness: Handedness,
    previous_landmarks: list[Landmark] | None,
    dt_seconds: float,
) -> HandKinematics:
    _x_axis, palm_direction, palm_normal = compute_palm_axes(landmarks, handedness)
    wrist = get_landmark(landmarks, LANDMARK_INDEX["WRIST"])
    previous_wrist = (
        get_landmark(previous_landmarks, LANDMARK_INDEX["WRIST"])
        if previous_landmarks is not None
        else None
    )
    wrist_velocity = (
        velocity_between(wrist, previous_wrist, dt_seconds)
        if previous_wrist is not None
        else zero_vec3()
    )
    return HandKinematics(
        palm_normal=palm_normal,
        palm_direction=palm_direction,
        finger_angles=compute_finger_angles(landmarks),
        wrist_velocity=wrist_velocity,
        fingertip_velocities=compute_fingertip_velocities(
            landmarks,
            previous_landmarks,
            dt_seconds,
        ),
    )


def palm_center(landmarks: list[Landmark]) -> Vec3:
    wrist = get_landmark(landmarks, LANDMARK_INDEX["WRIST"])
    index_mcp = get_landmark(landmarks, LANDMARK_INDEX["INDEX_MCP"])
    pinky_mcp = get_landmark(landmarks, LANDMARK_INDEX["PINKY_MCP"])
    return scale(add(add(wrist, index_mcp), pinky_mcp), 1.0 / 3.0)
