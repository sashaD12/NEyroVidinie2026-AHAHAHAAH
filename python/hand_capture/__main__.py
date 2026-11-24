from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from .camera import CameraStream
from .detector import HandDetector
from .overlay import draw_capture
from .pipeline import HandCapture
from .types import CaptureConfig, CaptureSmoothing, default_capture_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Базовый захват движения руки с камеры ноутбука"
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--max-hands", type=int, default=2)
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--no-smooth", action="store_true")
    parser.add_argument("--auto-exposure", action="store_true")
    parser.add_argument("--exposure", type=float, default=None)
    parser.add_argument("--record", type=Path, default=None)
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> CaptureConfig:
    config = default_capture_config()
    return CaptureConfig(
        presence_threshold=config.presence_threshold,
        max_hands=max(1, args.max_hands),
        smoothing=CaptureSmoothing(
            min_cutoff=config.smoothing.min_cutoff,
            beta=config.smoothing.beta,
            d_cutoff=config.smoothing.d_cutoff,
        ),
        enable_canonical_frame=config.enable_canonical_frame,
        enable_smoothing=not args.no_smooth,
    )


def next_timestamp(started_at: float, last_timestamp_ms: int) -> int:
    timestamp_ms = int((time.perf_counter() - started_at) * 1000.0)
    if timestamp_ms <= last_timestamp_ms:
        timestamp_ms = last_timestamp_ms + 1
    return timestamp_ms


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    config = build_config(args)
    mirrored = not args.no_mirror
    capture = CameraStream(
        args.camera,
        args.width,
        args.height,
        lock_auto_exposure=not args.auto_exposure,
        exposure=args.exposure,
    )
    detector = HandDetector(config.max_hands, config.presence_threshold)
    pipeline = HandCapture(config)
    record_file = args.record.open("w", encoding="utf-8") if args.record is not None else None
    started_at = time.perf_counter()
    last_timestamp_ms = -1
    last_frame_at = started_at
    fps = 0.0
    window_name = "Hand Motion Capture"
    print("Камера запущена. Покажи руку. Выход: Q")
    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    break
                continue
            if mirrored:
                frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]
            rgb: NDArray[np.uint8] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp_ms = next_timestamp(started_at, last_timestamp_ms)
            last_timestamp_ms = timestamp_ms
            detections = detector.detect(rgb, timestamp_ms, mirrored)
            result = pipeline.process(detections, float(timestamp_ms), width, height)
            now = time.perf_counter()
            instant_fps = 1.0 / max(now - last_frame_at, 1e-6)
            fps = instant_fps if fps <= 0.0 else fps * 0.9 + instant_fps * 0.1
            last_frame_at = now
            view = draw_capture(frame, result, fps)
            cv2.imshow(window_name, view)
            if record_file is not None:
                record_file.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break
    finally:
        detector.close()
        capture.release()
        cv2.destroyAllWindows()
        if record_file is not None:
            record_file.close()


if __name__ == "__main__":
    main()
