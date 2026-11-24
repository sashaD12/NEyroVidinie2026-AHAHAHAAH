export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface Landmark extends Vec3 {
  visibility?: number;
}

export interface ImageFrame {
  width: number;
  height: number;
  timestampMs: number;
  pixels?: ImageData | HTMLVideoElement | HTMLCanvasElement | OffscreenCanvas;
}

export interface RawHandDetection {
  landmarks: Landmark[];
  worldLandmarks?: Landmark[];
  handedness: "Left" | "Right";
  presenceScore: number;
}

export interface HandDetector {
  detect(frame: ImageFrame): RawHandDetection[] | Promise<RawHandDetection[]>;
}

export interface FingerAngles {
  mcp: number;
  pip: number;
  dip: number;
}

export interface FingertipVelocities {
  thumb: Vec3;
  index: Vec3;
  middle: Vec3;
  ring: Vec3;
  pinky: Vec3;
}

export interface HandKinematics {
  palmNormal: Vec3;
  palmDirection: Vec3;
  fingerAngles: {
    thumb: FingerAngles;
    index: FingerAngles;
    middle: FingerAngles;
    ring: FingerAngles;
    pinky: FingerAngles;
  };
  wristVelocity: Vec3;
  fingertipVelocities: FingertipVelocities;
}

export interface CapturedHand {
  handedness: "Left" | "Right";
  confidence: number;
  landmarks: Landmark[];
  worldLandmarks: Landmark[];
  canonicalLandmarks: Landmark[];
  kinematics: HandKinematics;
  isTracked: boolean;
}

export interface CaptureResult {
  timestampMs: number;
  frameWidth: number;
  frameHeight: number;
  hands: CapturedHand[];
}

export interface CaptureSmoothing {
  minCutoff: number;
  beta: number;
  dCutoff: number;
}

export interface CaptureConfig {
  presenceThreshold: number;
  maxHands: number;
  smoothing: CaptureSmoothing;
  enableCanonicalFrame: boolean;
}

export interface OneEuroFilterState {
  isInitialized: boolean;
  xPrev: number;
  dxPrev: number;
}

export interface LandmarkFilterState {
  x: OneEuroFilterState;
  y: OneEuroFilterState;
  z: OneEuroFilterState;
}

export interface HandFilterBank {
  image: LandmarkFilterState[];
  world: LandmarkFilterState[];
}

export interface FiltersByHand {
  Left?: HandFilterBank;
  Right?: HandFilterBank;
}

export interface LandmarksByHand {
  Left?: Landmark[];
  Right?: Landmark[];
}

export interface CaptureState {
  previousTimestampMs: number | null;
  filtersByHand: FiltersByHand;
  previousCanonicalByHand: LandmarksByHand;
  previousSmoothedByHand: LandmarksByHand;
}
