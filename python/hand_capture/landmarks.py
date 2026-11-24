from __future__ import annotations

from .types import Landmark, Vec3

LANDMARK_COUNT = 21

LANDMARK_NAMES: dict[int, str] = {
    0: "WRIST",
    1: "THUMB_CMC",
    2: "THUMB_MCP",
    3: "THUMB_IP",
    4: "THUMB_TIP",
    5: "INDEX_MCP",
    6: "INDEX_PIP",
    7: "INDEX_DIP",
    8: "INDEX_TIP",
    9: "MIDDLE_MCP",
    10: "MIDDLE_PIP",
    11: "MIDDLE_DIP",
    12: "MIDDLE_TIP",
    13: "RING_MCP",
    14: "RING_PIP",
    15: "RING_DIP",
    16: "RING_TIP",
    17: "PINKY_MCP",
    18: "PINKY_PIP",
    19: "PINKY_DIP",
    20: "PINKY_TIP",
}

FINGER_CHAINS: dict[str, list[int]] = {
    "thumb": [0, 1, 2, 3, 4],
    "index": [5, 6, 7, 8],
    "middle": [9, 10, 11, 12],
    "ring": [13, 14, 15, 16],
    "pinky": [17, 18, 19, 20],
}

BONE_CONNECTIONS: list[tuple[int, int]] = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (0, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (0, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (5, 9),
    (9, 13),
    (13, 17),
]

LANDMARK_INDEX: dict[str, int] = {
    "WRIST": 0,
    "THUMB_CMC": 1,
    "THUMB_MCP": 2,
    "THUMB_IP": 3,
    "THUMB_TIP": 4,
    "INDEX_MCP": 5,
    "INDEX_PIP": 6,
    "INDEX_DIP": 7,
    "INDEX_TIP": 8,
    "MIDDLE_MCP": 9,
    "MIDDLE_PIP": 10,
    "MIDDLE_DIP": 11,
    "MIDDLE_TIP": 12,
    "RING_MCP": 13,
    "RING_PIP": 14,
    "RING_DIP": 15,
    "RING_TIP": 16,
    "PINKY_MCP": 17,
    "PINKY_PIP": 18,
    "PINKY_DIP": 19,
    "PINKY_TIP": 20,
}

FINGER_JOINTS: dict[str, dict[str, tuple[int, int, int]]] = {
    "thumb": {"mcp": (0, 1, 2), "pip": (1, 2, 3), "dip": (2, 3, 4)},
    "index": {"mcp": (0, 5, 6), "pip": (5, 6, 7), "dip": (6, 7, 8)},
    "middle": {"mcp": (0, 9, 10), "pip": (9, 10, 11), "dip": (10, 11, 12)},
    "ring": {"mcp": (0, 13, 14), "pip": (13, 14, 15), "dip": (14, 15, 16)},
    "pinky": {"mcp": (0, 17, 18), "pip": (17, 18, 19), "dip": (18, 19, 20)},
}

FINGERTIP_INDEX: dict[str, int] = {
    "thumb": 4,
    "index": 8,
    "middle": 12,
    "ring": 16,
    "pinky": 20,
}


def get_landmark(landmarks: list[Landmark], index: int) -> Landmark:
    if index < 0 or index >= len(landmarks):
        return Landmark(x=0.0, y=0.0, z=0.0)
    landmark = landmarks[index]
    if landmark is None:
        return Landmark(x=0.0, y=0.0, z=0.0)
    return landmark


def clone_landmark(landmark: Landmark) -> Landmark:
    return Landmark(
        x=landmark.x,
        y=landmark.y,
        z=landmark.z,
        visibility=landmark.visibility,
    )


def clone_landmark_set(landmarks: list[Landmark]) -> list[Landmark]:
    cloned: list[Landmark] = []
    for index in range(len(landmarks)):
        landmark = landmarks[index]
        if landmark is None:
            cloned.append(Landmark(x=0.0, y=0.0, z=0.0))
        else:
            cloned.append(clone_landmark(landmark))
    return cloned


def ensure_landmark_count(landmarks: list[Landmark]) -> list[Landmark]:
    padded: list[Landmark] = []
    for index in range(LANDMARK_COUNT):
        if index >= len(landmarks):
            padded.append(Landmark(x=0.0, y=0.0, z=0.0))
            continue
        landmark = landmarks[index]
        if landmark is None:
            padded.append(Landmark(x=0.0, y=0.0, z=0.0))
        else:
            padded.append(clone_landmark(landmark))
    return padded


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(x=a.x - b.x, y=a.y - b.y, z=a.z - b.z)


def add(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(x=a.x + b.x, y=a.y + b.y, z=a.z + b.z)


def scale(vector: Vec3, scalar: float) -> Vec3:
    return Vec3(x=vector.x * scalar, y=vector.y * scalar, z=vector.z * scalar)


def dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def cross(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(
        x=a.y * b.z - a.z * b.y,
        y=a.z * b.x - a.x * b.z,
        z=a.x * b.y - a.y * b.x,
    )


def length(vector: Vec3) -> float:
    return dot(vector, vector) ** 0.5


def distance3(a: Vec3, b: Vec3) -> float:
    return length(subtract(a, b))


def normalize(vector: Vec3) -> Vec3:
    vector_length = length(vector)
    if vector_length <= 1e-8:
        return Vec3(x=0.0, y=0.0, z=0.0)
    return scale(vector, 1.0 / vector_length)


def clamp(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def zero_vec3() -> Vec3:
    return Vec3(x=0.0, y=0.0, z=0.0)
