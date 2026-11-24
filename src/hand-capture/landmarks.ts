import { Landmark, Vec3 } from "./types.js";

export const LANDMARK_COUNT = 21;

export const LANDMARK_NAMES = {
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
} as const;

export const FINGER_CHAINS = {
  thumb: [0, 1, 2, 3, 4],
  index: [5, 6, 7, 8],
  middle: [9, 10, 11, 12],
  ring: [13, 14, 15, 16],
  pinky: [17, 18, 19, 20],
} as const;

export const BONE_CONNECTIONS = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [0, 5],
  [5, 6],
  [6, 7],
  [7, 8],
  [0, 9],
  [9, 10],
  [10, 11],
  [11, 12],
  [0, 13],
  [13, 14],
  [14, 15],
  [15, 16],
  [0, 17],
  [17, 18],
  [18, 19],
  [19, 20],
  [5, 9],
  [9, 13],
  [13, 17],
] as const;

export const LANDMARK_INDEX = {
  WRIST: 0,
  THUMB_CMC: 1,
  THUMB_MCP: 2,
  THUMB_IP: 3,
  THUMB_TIP: 4,
  INDEX_MCP: 5,
  INDEX_PIP: 6,
  INDEX_DIP: 7,
  INDEX_TIP: 8,
  MIDDLE_MCP: 9,
  MIDDLE_PIP: 10,
  MIDDLE_DIP: 11,
  MIDDLE_TIP: 12,
  RING_MCP: 13,
  RING_PIP: 14,
  RING_DIP: 15,
  RING_TIP: 16,
  PINKY_MCP: 17,
  PINKY_PIP: 18,
  PINKY_DIP: 19,
  PINKY_TIP: 20,
} as const;

export function getLandmark(landmarks: Landmark[], index: number): Landmark {
  const landmark = landmarks[index];
  if (!landmark) {
    return { x: 0, y: 0, z: 0 };
  }
  return landmark;
}

export function cloneLandmark(landmark: Landmark): Landmark {
  const cloned: Landmark = {
    x: landmark.x,
    y: landmark.y,
    z: landmark.z,
  };
  if (landmark.visibility !== undefined) {
    cloned.visibility = landmark.visibility;
  }
  return cloned;
}

export function cloneLandmarkSet(landmarks: Landmark[]): Landmark[] {
  const cloned: Landmark[] = [];
  for (let index = 0; index < landmarks.length; index += 1) {
    const landmark = landmarks[index];
    if (!landmark) {
      cloned.push({ x: 0, y: 0, z: 0 });
    } else {
      cloned.push(cloneLandmark(landmark));
    }
  }
  return cloned;
}

export function ensureLandmarkCount(landmarks: Landmark[]): Landmark[] {
  const padded: Landmark[] = [];
  for (let index = 0; index < LANDMARK_COUNT; index += 1) {
    const landmark = landmarks[index];
    if (!landmark) {
      padded.push({ x: 0, y: 0, z: 0 });
    } else {
      padded.push(cloneLandmark(landmark));
    }
  }
  return padded;
}

export function subtract(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.x - b.x,
    y: a.y - b.y,
    z: a.z - b.z,
  };
}

export function add(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.x + b.x,
    y: a.y + b.y,
    z: a.z + b.z,
  };
}

export function scale(vector: Vec3, scalar: number): Vec3 {
  return {
    x: vector.x * scalar,
    y: vector.y * scalar,
    z: vector.z * scalar,
  };
}

export function dot(a: Vec3, b: Vec3): number {
  return a.x * b.x + a.y * b.y + a.z * b.z;
}

export function cross(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

export function length(vector: Vec3): number {
  return Math.sqrt(dot(vector, vector));
}

export function distance3(a: Vec3, b: Vec3): number {
  return length(subtract(a, b));
}

export function normalize(vector: Vec3): Vec3 {
  const vectorLength = length(vector);
  if (vectorLength <= 1e-8) {
    return { x: 0, y: 0, z: 0 };
  }
  return scale(vector, 1 / vectorLength);
}

export function clamp(value: number, minValue: number, maxValue: number): number {
  if (value < minValue) {
    return minValue;
  }
  if (value > maxValue) {
    return maxValue;
  }
  return value;
}
