import numpy as np, cv2, time
from sklearn.svm import LinearSVC
from common import *
rng = np.random.default_rng(1)
pos, neg = [], []
scenes = [make_scene(rng) for _ in range(250)]
scenes = [(degrade(img, 1.0, 0, 0, rng).astype(np.float32), b) for img, b in scenes]   # звичайний шум сенсора за нормальної експозиції
for img, boxes in scenes:
    u8 = img.astype(np.uint8)
    for (x, y, w, h) in boxes:
        for jit in range(3):
            p = int(round(w * 0.0)); dx, dy = rng.integers(-2, 3, 2)
            x0, y0 = max(0, x + dx), max(0, y + dy)
            crop = u8[y0:y0 + w, x0:x0 + w]
            pos.append(patch_feat(crop)); pos.append(patch_feat(cv2.flip(crop, 1)))
    for _ in range(25):
        s = int(rng.integers(30, 80)); x, y = int(rng.integers(0, W - s)), int(rng.integers(0, H - s))
        if all(iou((x, y, s, s), b) < 0.2 for b in boxes):
            neg.append(patch_feat(u8[y:y + s, x:x + s]))
X = np.array(pos + neg); y = np.array([1] * len(pos) + [0] * len(neg))
clf = LinearSVC(C=0.05, max_iter=50000).fit(X, y)
det = Detector(clf.coef_.ravel(), clf.intercept_[0])
hard = []
for img, boxes in scenes[:150]:
    d, s = det.detect(img.astype(np.uint8), hit=0.0)
    for r in d:
        if all(iou(r, b) < 0.3 for b in boxes):
            x, yy, w, h = [int(v) for v in r]
            pc = img.astype(np.uint8)[max(yy,0):yy + h, max(x,0):x + w]
            if pc.shape[0] > 8 and pc.shape[1] > 8: hard.append(patch_feat(pc))
print('pos', len(pos), 'neg', len(neg), 'hard', len(hard))
X = np.vstack([X, np.array(hard)]); y = np.concatenate([y, np.zeros(len(hard), int)])
clf = LinearSVC(C=0.05, max_iter=50000).fit(X, y)
np.save('svm.npy', np.append(clf.coef_.ravel(), clf.intercept_[0]))
