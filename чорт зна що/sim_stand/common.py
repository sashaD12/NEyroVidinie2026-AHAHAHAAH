"""Синтетичний стенд: генерація сцен, деградації, маршрути, детектор, Контур 1."""
import numpy as np, cv2, time

W, H = 640, 360

# ---------------- генерація сцени ----------------
def _smooth_noise(rng, h, w, scale):
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)

def make_background(rng):
    bg = np.zeros((H, W), np.float32)
    for sc, amp in [(120, 60), (40, 30), (12, 14), (4, 8)]:
        bg += amp * (_smooth_noise(rng, H, W, sc) - 0.5)
    bg += rng.uniform(95, 150)
    # дороги/межі полів
    for _ in range(rng.integers(1, 4)):
        p1 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
        p2 = (int(rng.integers(0, W)), int(rng.integers(0, H)))
        cv2.line(bg, p1, p2, float(rng.uniform(70, 190)), int(rng.integers(6, 16)))
    # хибні цілі: однорідні прямокутники без внутрішньої структури
    for _ in range(rng.integers(2, 6)):
        w, h = int(rng.integers(25, 70)), int(rng.integers(25, 70))
        x, y = int(rng.integers(0, W - w)), int(rng.integers(0, H - h))
        cv2.rectangle(bg, (x, y), (x + w, y + h), float(rng.uniform(60, 200)), -1)
    return bg

def draw_object(img, x, y, s, rng):
    """Об'єкт («техніка» зверху): корпус, тінь, темна кабіна, світлий кузов."""
    base = img[y:y + s, x:x + s].mean()
    sign = 1 if rng.random() < 0.5 else -1
    body = float(np.clip(base + sign * rng.uniform(25, 55), 10, 245))
    cv2.rectangle(img, (x + 4, y + 4), (x + s + 2, y + s + 2), float(max(base - 40, 5)), -1)   # тінь
    cv2.rectangle(img, (x, y), (x + s - 1, y + s - 1), body, -1)
    m = s // 5
    cabin = float(np.clip(body - sign * 60 - 20, 0, 255))
    cv2.rectangle(img, (x + m, y + m), (x + s - m, y + s // 2 - 2), cabin, -1)
    cv2.rectangle(img, (x + m, y + s // 2 + 2), (x + s - m, y + s - m), float(np.clip(body + 25, 0, 255)), 2)

def make_scene(rng, n_min=4, n_max=8):
    img = make_background(rng)
    boxes = []
    n = int(rng.integers(n_min, n_max + 1)); tries = 0
    while len(boxes) < n and tries < 200:
        tries += 1
        s = int(rng.integers(24, 48))
        x, y = int(rng.integers(2, W - s - 6)), int(rng.integers(2, H - s - 6))
        if any(not (x + s + 8 < bx or bx + bs + 8 < x or y + s + 8 < by or by + bs + 8 < y) for bx, by, bs in boxes):
            continue
        draw_object(img, x, y, s, rng); boxes.append((x, y, s))
    img = cv2.GaussianBlur(img, (3, 3), 0.7)          # оптика камери
    return np.clip(img, 0, 255).astype(np.float32), [(x, y, s, s) for x, y, s in boxes]

# ---------------- деградації (контрольовані рівні) ----------------
EXPOSURE = [1.0, 0.5, 0.3, 0.15]     # коефіцієнт експозиції
NOISE    = [0, 5, 10, 20]            # СКВ шуму сенсора, рівні яскравості
BLUR     = [0, 5, 9, 15]             # довжина ядра змазування руху, пікселі

def motion_kernel(L, angle):
    k = np.zeros((L, L), np.float32); k[L // 2, :] = 1
    M = cv2.getRotationMatrix2D((L / 2 - 0.5, L / 2 - 0.5), angle, 1.0)
    k = cv2.warpAffine(k, M, (L, L)); return k / k.sum()

def degrade(img, e, sigma, L, rng):
    out = img.copy()
    if L > 0:
        out = cv2.filter2D(out, -1, motion_kernel(L, rng.uniform(0, 180)))
    out = out * e
    std = np.sqrt(2.0 ** 2 + 0.05 * np.maximum(out, 0) + sigma ** 2)   # read + shot + додатковий
    out = out + rng.normal(0, 1, out.shape).astype(np.float32) * std
    return np.clip(np.round(out), 0, 255).astype(np.uint8)

# ---------------- маршрути (відомі операції OpenCV) ----------------
def _gamma_lut(img):
    m = max(img.mean(), 1.0) / 255.0
    g = float(np.clip(np.log(0.45) / np.log(m), 0.25, 1.0))
    return cv2.LUT(img, (255 * (np.arange(256) / 255.0) ** g).astype(np.uint8))
_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
def _unsharp(img):
    b = cv2.GaussianBlur(img, (0, 0), 2.0)
    return cv2.addWeighted(img, 1.8, b, -0.8, 0)
def _nlm(img):
    return cv2.fastNlMeansDenoising(img, None, h=15, templateWindowSize=7, searchWindowSize=21)

ROUTES = {
    'R0_none':        lambda im: im,
    'R1_gamma':       _gamma_lut,
    'R2_clahe':       lambda im: _clahe.apply(im),
    'R3_gauss':       lambda im: cv2.GaussianBlur(im, (5, 5), 1.2),
    'R4_unsharp':     _unsharp,
    'R5_bilat_gamma': lambda im: _gamma_lut(cv2.bilateralFilter(im, 7, 40, 7)),
    'R6_nlm':         _nlm,
    'R7_nlm_gamma':   lambda im: _gamma_lut(_nlm(im)),
}
ROUTE_NAMES = list(ROUTES)

# ---------------- Контур 1 (за описом учня; Лапласіан на повнороздільних сусідах) ----------------
def contour1(img, lap='grid'):
    """lap='grid' — Лапласіан на прорідженій сітці (варіант учня); lap='full' — за повнороздільними сусідами вузлів."""
    h, w = img.shape
    dx, dy = max(1, w // 160), max(1, h // 120)
    ys = (np.arange(120) * dy).clip(1, h - 2); xs = (np.arange(160) * dx).clip(1, w - 2)
    Y, X = np.meshgrid(ys, xs, indexing='ij')
    I = img.astype(np.float32)
    g = I[Y, X]
    N = g.size
    mu = g.mean(); var = max(float((g * g).mean() - mu * mu), 0.0); sig = np.sqrt(var)
    pb = (g <= 10).mean(); ps = (g >= 245).mean(); pdark = (g <= 55).mean()
    mu0, mu1, s0, pmax = 80, 180, 40, 0.5
    du = np.clip(max((mu0 - mu) / mu0, pb / pmax, pdark / 0.75), 0, 1)
    do = np.clip(max((mu - mu1) / (255 - mu1), ps / pmax), 0, 1)
    dc = np.clip(1 - sig / s0, 0, 1)
    if lap == 'full':
        L = I[Y, X + 1] + I[Y, X - 1] + I[Y + 1, X] + I[Y - 1, X] - 4 * g
    else:   # сусіди — сусідні вузли сітки (крок dx, dy); лише внутрішні вузли
        L = g[1:-1, 2:] + g[1:-1, :-2] + g[2:, 1:-1] + g[:-2, 1:-1] - 4 * g[1:-1, 1:-1]
    sL = float(L.var())
    db = np.clip(1 - sL / 100.0, 0, 1)
    nb = sum(I[Y + j, X + i] for j in (-1, 0, 1) for i in (-1, 0, 1)) / 9.0
    R = np.abs(g - nb)
    grad = np.abs(I[Y, X + 1] - I[Y, X - 1]) + np.abs(I[Y + 1, X] - I[Y - 1, X])
    F = grad < 24
    nflat = float(R[F].mean()) if F.any() else 0.0
    dn = np.clip(nflat / 8.0, 0, 1)
    return np.array([du, do, dc, dn, db], np.float32)

# ---------------- детектор (HOG + лінійний SVM за схемою Dalal–Triggs, навчений лише на чистих кадрах) ----------------
CELL, NB = 8, 9
WIN_CELLS = 4                      # вікно 32x32 = 4x4 комірки = 3x3 блоки
_CID = {}
def _cell_index(hc, wc):
    key = (hc, wc)
    if key not in _CID:
        r = np.arange(hc * CELL) // CELL; c = np.arange(wc * CELL) // CELL
        _CID[key] = ((r[:, None] * wc + c[None, :]) * NB).astype(np.int64)
    return _CID[key]

def hog_blocks(img):
    """Карта блокових ознак: (Hb, Wb, 36+4): HOG 2x2 комірки (L2-Hys) + середня яскравість 4 комірок."""
    f = img.astype(np.float32)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=1); gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=1)
    mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
    hc, wc = f.shape[0] // CELL, f.shape[1] // CELL
    mag = mag[:hc * CELL, :wc * CELL]; ang = np.mod(ang[:hc * CELL, :wc * CELL], 180.0)
    b = ang / (180.0 / NB) - 0.5
    b0 = np.floor(b); w1 = b - b0; b0 = np.mod(b0, NB).astype(np.int8)
    m0 = mag * (1 - w1); m1 = mag * w1; b1 = np.mod(b0 + 1, NB)
    cid = _cell_index(hc, wc)
    n = hc * wc * NB
    hist = (np.bincount((cid + b0).ravel(), m0.ravel(), n) +
            np.bincount((cid + b1).ravel(), m1.ravel(), n)).reshape(hc, wc, NB).astype(np.float32)
    blk = np.concatenate([hist[:-1, :-1], hist[:-1, 1:], hist[1:, :-1], hist[1:, 1:]], axis=2)
    blk = blk / np.sqrt((blk ** 2).sum(2, keepdims=True) + 1e-3)
    blk = np.minimum(blk, 0.2)
    blk = blk / np.sqrt((blk ** 2).sum(2, keepdims=True) + 1e-3)
    cm = f[:hc * CELL, :wc * CELL].reshape(hc, CELL, wc, CELL).mean((1, 3)) / 255.0
    cmb = np.stack([cm[:-1, :-1], cm[:-1, 1:], cm[1:, :-1], cm[1:, 1:]], axis=2)
    return np.concatenate([blk, cmb], axis=2).astype(np.float32)

def window_feats(blk):
    """Усі вікна 3x3 блоки -> (ny, nx, 324)."""
    k = WIN_CELLS - 1
    v = np.lib.stride_tricks.sliding_window_view(blk, (k, k), axis=(0, 1))   # (ny,nx,36,k,k)
    return v.transpose(0, 1, 3, 4, 2).reshape(v.shape[0], v.shape[1], -1)

def patch_feat(patch):
    p = cv2.resize(patch, (WIN_CELLS * CELL, WIN_CELLS * CELL), interpolation=cv2.INTER_AREA)
    return window_feats(hog_blocks(p))[0, 0]

def nms_boxes(b, s, thr):
    x1, y1 = b[:, 0], b[:, 1]; x2, y2 = b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    area = b[:, 2] * b[:, 3]; order = np.argsort(-s); keep = []
    while order.size:
        i = order[0]; keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]]); yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]]); yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        ov = inter / (area[i] + area[order[1:]] - inter + 1e-9)
        order = order[1:][ov <= thr]
    return np.array(keep, int)

class Detector:
    def __init__(self, w, b):
        self.w = w.astype(np.float32); self.b = float(b)
    def detect(self, img, hit=-0.5, scale=1.15, nms=0.3):
        boxes, scores = [], []
        s = 0.75; cur = cv2.resize(img, (int(img.shape[1] / s), int(img.shape[0] / s)), interpolation=cv2.INTER_LINEAR)
        while cur.shape[0] >= 40 and cur.shape[1] >= 40 and s < 1.9:
            for off in (0,):
                sub = cur[off:, off:]
                if sub.shape[0] < 32 or sub.shape[1] < 32: continue
                wf = window_feats(hog_blocks(sub))
                sc = wf @ self.w + self.b
                ys, xs = np.where(sc > hit)
                for yy, xx in zip(ys, xs):
                    boxes.append([(xx * CELL + off) * s, (yy * CELL + off) * s, 32 * s, 32 * s]); scores.append(sc[yy, xx])
            s *= scale
            cur = cv2.resize(img, (int(img.shape[1] / s), int(img.shape[0] / s)), interpolation=cv2.INTER_AREA)
        if not boxes:
            return np.zeros((0, 4), np.float32), np.zeros(0, np.float32)
        boxes = np.asarray(boxes, np.float32); scores = np.asarray(scores, np.float32)
        keep = nms_boxes(boxes, scores, nms)
        return boxes[keep], scores[keep]

def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)

def match(dets, scores, gts, thr=0.5):
    """Повертає список (score, tp) для кожної детекції, жадібне зіставлення за IoU>=thr."""
    order = np.argsort(-scores); used = set(); out = []
    for i in order:
        best, bj = 0, -1
        for j, g in enumerate(gts):
            if j in used: continue
            v = iou(dets[i], g)
            if v > best: best, bj = v, j
        if best >= thr: used.add(bj); out.append((float(scores[i]), 1))
        else: out.append((float(scores[i]), 0))
    return out

def ap_from_matches(matches, n_gt):
    if n_gt == 0: return 0.0
    if not matches: return 0.0
    m = sorted(matches, key=lambda t: -t[0])
    tp = np.cumsum([t[1] for t in m]); fp = np.cumsum([1 - t[1] for t in m])
    rec = tp / n_gt; prec = tp / np.maximum(tp + fp, 1e-9)
    mrec = np.concatenate([[0], rec, [1]]); mpre = np.concatenate([[0], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1): mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))

def f1_at(matches, n_gt, conf):
    tp = sum(1 for s, t in matches if s >= conf and t); fp = sum(1 for s, t in matches if s >= conf and not t)
    fn = n_gt - tp
    return 2 * tp / max(2 * tp + fp + fn, 1)
