from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from hand_capture.camera import CameraStream
from hand_capture.detector import HandDetector
from hand_capture.pipeline import HandCapture
from hand_capture.types import CaptureConfig, CaptureSmoothing, default_capture_config

from .engine import DEFAULT_COLOR, DEFAULT_THICKNESS, MotionSafety, SketchCanvas, command_from_result
from .view import render_view

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Air-sketch test: fingertip draw, other hand color/size")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--auto-exposure", action="store_true")
    return parser.parse_args()


def next_timestamp(started_at: float, last_timestamp_ms: int) -> int:
    timestamp_ms = int((time.perf_counter() - started_at) * 1000.0)
    if timestamp_ms <= last_timestamp_ms:
        timestamp_ms = last_timestamp_ms + 1
    return timestamp_ms


def save_canvas(canvas: SketchCanvas) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"sketch_{stamp}.png"
    canvas.save_png(str(path))
    return str(path)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    mirrored = not args.no_mirror
    config = default_capture_config()
    capture_config = CaptureConfig(
        presence_threshold=config.presence_threshold,
        max_hands=2,
        smoothing=CaptureSmoothing(
            min_cutoff=config.smoothing.min_cutoff,
            beta=config.smoothing.beta,
            d_cutoff=config.smoothing.d_cutoff,
        ),
        enable_canonical_frame=config.enable_canonical_frame,
        enable_smoothing=config.enable_smoothing,
    )
    capture = CameraStream(
        args.camera,
        args.width,
        args.height,
        lock_auto_exposure=not args.auto_exposure,
    )
    detector = HandDetector(2, capture_config.presence_threshold)
    pipeline = HandCapture(capture_config)
    canvas = SketchCanvas(args.width, args.height)
    safety = MotionSafety()
    color = DEFAULT_COLOR
    thickness = DEFAULT_THICKNESS
    hue = 0.0
    status = ""
    status_until = 0.0
    started_at = time.perf_counter()
    last_timestamp_ms = -1
    window_name = "Air Sketch"
    print("Air-sketch. Кулак — предохранитель, кулак→палец — взведение. S — PNG, C — очистка, Q — выход")
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
            canvas.resize(width, height)
            rgb: NDArray[np.uint8] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp_ms = next_timestamp(started_at, last_timestamp_ms)
            last_timestamp_ms = timestamp_ms
            detections = detector.detect(rgb, timestamp_ms, mirrored)
            result = pipeline.process(detections, float(timestamp_ms), width, height)
            command = command_from_result(result, color, thickness, hue)
            command = safety.filter(command, float(timestamp_ms))
            color = command.color
            thickness = command.thickness
            hue = command.hue
            canvas.apply(command)
            if time.perf_counter() > status_until:
                status = ""
            view = render_view(frame, canvas, command, status)
            cv2.imshow(window_name, view)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break
            if key == ord("c"):
                canvas.clear()
                status = "cleared"
                status_until = time.perf_counter() + 1.6
            if key == ord("s"):
                saved = save_canvas(canvas)
                status = saved
                status_until = time.perf_counter() + 2.5
                print(f"PNG: {saved}")
    finally:
        detector.close()
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
