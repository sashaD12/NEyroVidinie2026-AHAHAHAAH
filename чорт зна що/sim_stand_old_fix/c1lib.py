"""Виклик C-бібліотеки Контуру 1 (вектор, власні маршрути, селектор) зі стенду через ctypes."""
import ctypes
import os
import sys

import numpy as np

C_DIR_NAME = "contour_1_old_fix"
HERE = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.environ.get("C1_LIB_DIR", os.path.join(HERE, "..", "..", "c", C_DIR_NAME, "bin"))
LIB_NAME = "contour_1.dll" if sys.platform == "win32" else "libcontour_1.so"
LIB_PATH = os.path.abspath(os.path.join(LIB_DIR, LIB_NAME))

_lib = ctypes.CDLL(LIB_PATH)
_u8p = ctypes.POINTER(ctypes.c_uint8)
_f32p = ctypes.POINTER(ctypes.c_float)
_int = ctypes.c_int

_lib.ad_py_assess.argtypes = [_u8p, _int, _int, _int, _f32p, _f32p]
_lib.ad_py_assess.restype = _int
_lib.ad_py_route.argtypes = [_u8p, _int, _int, _int, _int, _f32p]
_lib.ad_py_route.restype = _int
_lib.ad_py_select.argtypes = [_f32p]
_lib.ad_py_select.restype = _int
_lib.ad_py_diag_size.restype = _int
_lib.ad_py_route_count.restype = _int
_lib.ad_py_config_values.argtypes = [_f32p, _int]
_lib.ad_py_config_values.restype = _int

DIAG = _lib.ad_py_diag_size()
ROUTE_COUNT = _lib.ad_py_route_count()
KINDS = ["none", "under", "over", "contrast", "mixed", "noise", "blur"]
STATES = ["ok", "repair", "bad"]
DIAG_NAMES = ["s_L", "n_flat", "flat_count", "aniso", "e_max", "d_motion",
              "log_kind", "log_state", "log_r", "mu", "sigma", "sample_count", "s_L_raw", "noise_sigma"]


def assess(img):
    a = np.ascontiguousarray(img, dtype=np.uint8)
    q = np.zeros(5, np.float32)
    d = np.zeros(DIAG, np.float32)
    _lib.ad_py_assess(a.ctypes.data_as(_u8p), a.shape[1], a.shape[0], a.strides[0],
                      q.ctypes.data_as(_f32p), d.ctypes.data_as(_f32p))
    return q, d


def route(img, rid, q):
    out = np.array(img, dtype=np.uint8, order="C", copy=True)
    v = np.ascontiguousarray(q, dtype=np.float32)
    _lib.ad_py_route(out.ctypes.data_as(_u8p), out.shape[1], out.shape[0], out.strides[0], rid,
                     v.ctypes.data_as(_f32p))
    return out


def select(q):
    v = np.ascontiguousarray(q, dtype=np.float32)
    return _lib.ad_py_select(v.ctypes.data_as(_f32p))


def config():
    out = np.zeros(3, np.float32)
    _lib.ad_py_config_values(out.ctypes.data_as(_f32p), 3)
    return dict(s_L0=float(out[0]), n0=float(out[1]), flat_frac=float(out[2]))
