from __future__ import annotations

import ctypes
import sys
import threading
import time

import cv2
import numpy as np
from numpy.typing import NDArray

MIN_LIVE_LUMA = 4.0
COINIT_APARTMENTTHREADED = 0x2


def _com_initialize() -> None:
    if sys.platform != "win32":
        return
    ctypes.windll.ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)


def _com_uninitialize() -> None:
    if sys.platform != "win32":
        return
    ctypes.windll.ole32.CoUninitialize()


def try_set(capture: cv2.VideoCapture, prop: int, value: float) -> None:
    current = capture.get(prop)
    if current == -1.0:
        return
    capture.set(prop, value)


def configure_capture(capture: cv2.VideoCapture, width: int, height: int) -> None:
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    capture.set(cv2.CAP_PROP_FPS, 30.0)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1.0)


def _backends() -> list[int]:
    if sys.platform == "win32":
        return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    return [cv2.CAP_ANY]


def _probe_frame(capture: cv2.VideoCapture) -> bool:
    for _index in range(8):
        ok, frame = capture.read()
        if ok and frame is not None and frame.size > 0:
            return True
    return False


def open_capture(index: int, width: int, height: int) -> cv2.VideoCapture:
    last_error = f"Не удалось открыть камеру {index}"
    for backend in _backends():
        capture = cv2.VideoCapture(index, backend)
        if not capture.isOpened():
            capture.release()
            last_error = f"Камера {index} не открылась (backend {backend})"
            continue
        configure_capture(capture, width, height)
        if _probe_frame(capture):
            return capture
        last_error = f"Камера {index} не отдаёт кадры (backend {backend})"
        capture.release()
    raise RuntimeError(last_error)


def frame_luma(frame: NDArray[np.uint8]) -> float:
    return float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean())


def lock_exposure(capture: cv2.VideoCapture, exposure: float | None = None) -> None:
    auto_value = capture.get(cv2.CAP_PROP_AUTO_EXPOSURE)
    current_exposure = capture.get(cv2.CAP_PROP_EXPOSURE)
    if auto_value == -1.0:
        return
    locked_exposure = exposure if exposure is not None else current_exposure
    if locked_exposure == 0.0 or locked_exposure == -1.0:
        locked_exposure = current_exposure
    for mode in (0.25, 0.0, 1.0):
        capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, mode)
        if locked_exposure != -1.0 and locked_exposure != 0.0:
            capture.set(cv2.CAP_PROP_EXPOSURE, locked_exposure)
        next_auto = capture.get(cv2.CAP_PROP_AUTO_EXPOSURE)
        if abs(next_auto - 0.75) > 0.05 and abs(next_auto - 3.0) > 0.05:
            break
    try_set(capture, cv2.CAP_PROP_AUTOFOCUS, 0.0)
    try_set(capture, cv2.CAP_PROP_AUTO_WB, 0.0)
    try_set(capture, cv2.CAP_PROP_BACKLIGHT, 0.0)


def stabilize_luma(
    frame: NDArray[np.uint8],
    target_luma: float,
    previous_gain: float,
) -> tuple[NDArray[np.uint8], float]:
    current = frame_luma(frame)
    if current <= MIN_LIVE_LUMA:
        return frame, previous_gain
    raw_gain = target_luma / current
    if raw_gain < 0.6:
        raw_gain = 0.6
    if raw_gain > 1.8:
        raw_gain = 1.8
    gain = previous_gain * 0.65 + raw_gain * 0.35
    if abs(gain - 1.0) < 0.03:
        return frame, gain
    return cv2.convertScaleAbs(frame, alpha=gain, beta=0.0), gain


class CameraStream:
    def __init__(
        self,
        index: int,
        width: int,
        height: int,
        lock_auto_exposure: bool = True,
        exposure: float | None = None,
    ) -> None:
        self._index = index
        self._width = width
        self._height = height
        self._lock_auto_exposure = lock_auto_exposure
        self._exposure = exposure
        self._lock = threading.Lock()
        self._frame: NDArray[np.uint8] | None = None
        self._ok = False
        self._stopped = False
        self._error: str | None = None
        self._ready = threading.Event()
        self._sync: cv2.VideoCapture | None = None
        self._thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()
        if self._ready.wait(timeout=8.0) and self._error is None:
            return
        self._stopped = True
        self._thread.join(timeout=1.5)
        if self._error is not None:
            thread_error = self._error
        else:
            thread_error = "поток камеры не получил кадр"
        try:
            self._sync = self._open_sync()
        except Exception as exc:
            raise RuntimeError(f"Камера не запустилась ({thread_error}; {exc})") from exc

    def _open_sync(self) -> cv2.VideoCapture:
        capture = open_capture(self._index, self._width, self._height)
        if self._lock_auto_exposure:
            lock_exposure(capture, self._exposure)
        return capture

    def _store(self, frame: NDArray[np.uint8]) -> None:
        cloned = frame.copy()
        with self._lock:
            self._ok = True
            self._frame = cloned

    def _grab_loop(self) -> None:
        capture: cv2.VideoCapture | None = None
        com_ready = False
        try:
            _com_initialize()
            com_ready = True
            capture = open_capture(self._index, self._width, self._height)
            if self._lock_auto_exposure:
                lock_exposure(capture, self._exposure)
            target_luma = 0.0
            live_count = 0
            gain = 1.0
            has_frame = False
            while not self._stopped:
                ok, frame = capture.read()
                if not ok or frame is None:
                    time.sleep(0.005)
                    continue
                luma = frame_luma(frame)
                if luma > MIN_LIVE_LUMA:
                    live_count += 1
                    if live_count <= 6:
                        target_luma += luma
                    if live_count == 6:
                        target_luma = target_luma / 6.0
                    if self._lock_auto_exposure and live_count >= 6:
                        frame, gain = stabilize_luma(frame, target_luma, gain)
                elif has_frame:
                    continue
                self._store(frame)
                has_frame = True
                if not self._ready.is_set():
                    self._ready.set()
            return
        except Exception as exc:
            self._error = str(exc)
            self._ready.set()
        finally:
            if capture is not None:
                capture.release()
            if com_ready:
                _com_uninitialize()

    def read(self) -> tuple[bool, NDArray[np.uint8] | None]:
        if self._sync is not None:
            ok, frame = self._sync.read()
            if not ok or frame is None:
                return False, None
            return True, frame
        with self._lock:
            if self._frame is None:
                return False, None
            return self._ok, self._frame.copy()

    def release(self) -> None:
        self._stopped = True
        self._thread.join(timeout=1.5)
        if self._sync is not None:
            self._sync.release()
            self._sync = None
