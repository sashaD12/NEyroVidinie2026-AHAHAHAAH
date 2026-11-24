"""Перерахунок вектора Контуру 1 для вже зібраних кадрів: кадри відтворюються з тих самих зерен
(генерація сцени та деградація — єдині споживачі генератора), детекції й час маршрутів беруться зі збору."""
import numpy as np, pickle, time, sys, os
from common import *
mode, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
chunks = [('train', 100, 1001, '0'), ('train', 100, 1002, '1'), ('train', 100, 1003, '2'), ('train', 100, 1004, '3'),
          ('test', 100, 2001, '0'), ('test', 75, 2002, '1'), ('test', 75, 2003, '2')]
maxdev = 0.0
for split, n, seed, ch in chunks:
    recs = pickle.load(open(f'{split}_{ch}.pkl', 'rb')); rng = np.random.default_rng(seed)
    for k in range(n):
        img, boxes = make_scene(rng)
        e, s, L = rng.choice(EXPOSURE), rng.choice(NOISE), rng.choice(BLUR)
        d = degrade(img, e, s, L, rng)
        r = recs[k]
        assert (e, s, L) == (r['e'], r['sigma'], r['L']) and len(boxes) == r['n_gt']
        maxdev = max(maxdev, float(np.abs(contour1(d, 'full') - r['q']).max()))   # перевірка тотожності кадрів
        contour1(d, mode); ts = []
        for _ in range(3):
            t = time.perf_counter(); q = contour1(d, mode); ts.append(time.perf_counter() - t)
        r['q'] = q; r['t_c1'] = float(np.median(ts))
    pickle.dump(recs, open(f'{outdir}/{split}_{ch}.pkl', 'wb'))
print('макс. відхилення відтвореного q (full) від збереженого:', maxdev)
