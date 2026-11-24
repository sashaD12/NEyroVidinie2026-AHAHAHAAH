"""Збір даних: для кожного кадру — випадкова деградація з контрольованої сітки рівнів,
Контур 1, усі маршрути, детекція після кожного маршруту, виміряний час кожного етапу."""
import numpy as np, cv2, time, pickle, sys
from common import *
split, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
chunk = sys.argv[4] if len(sys.argv) > 4 else "0"
svm = np.load('svm.npy'); det = Detector(svm[:-1], svm[-1])
rng = np.random.default_rng(seed)
recs = []
for k in range(n):
    img, boxes = make_scene(rng)
    e, s, L = rng.choice(EXPOSURE), rng.choice(NOISE), rng.choice(BLUR)
    d = degrade(img, e, s, L, rng)
    t = time.perf_counter(); q = contour1(d); t_c1 = time.perf_counter() - t
    r = dict(e=e, sigma=s, L=L, n_gt=len(boxes), q=q, t_c1=t_c1, routes={})
    for rn, f in ROUTES.items():
        t = time.perf_counter(); out = f(d); t_r = time.perf_counter() - t
        t = time.perf_counter(); dd, sc = det.detect(out); t_d = time.perf_counter() - t
        r['routes'][rn] = dict(t_route=t_r, t_det=t_d, matches=match(dd, sc, boxes),
                               max_score=float(sc.max()) if len(sc) else -9.0)
    recs.append(r)
    if k % 25 == 0: print(split, k, flush=True)
pickle.dump(recs, open(f'{split}_{chunk}.pkl', 'wb'))
print('done', split)
