"""Перерахунок вектора Контуру 1 (нова версія) для вже зібраних кадрів: кадри відтворюються з тих самих зерен,
детекції й час маршрутів беруться зі збору старого стенду."""
import numpy as np, pickle, time, sys, os
from common import *
src = sys.argv[1] if len(sys.argv) > 1 else "data"
outdir = sys.argv[2] if len(sys.argv) > 2 else "."
os.makedirs(outdir, exist_ok=True)
chunks = [("train", 100, 1001, "0"), ("train", 100, 1002, "1"), ("train", 100, 1003, "2"), ("train", 100, 1004, "3"),
          ("test", 100, 2001, "0"), ("test", 75, 2002, "1"), ("test", 75, 2003, "2")]
maxdev = 0.0
for split, n, seed, ch in chunks:
    recs = pickle.load(open(f"{src}/{split}_{ch}.pkl", "rb")); rng = np.random.default_rng(seed)
    for k in range(n):
        img, boxes = make_scene(rng)
        e, s, L = rng.choice(EXPOSURE), rng.choice(NOISE), rng.choice(BLUR)
        d = degrade(img, e, s, L, rng)
        r = recs[k]
        assert (e, s, L) == (r["e"], r["sigma"], r["L"]) and len(boxes) == r["n_gt"]
        maxdev = max(maxdev, float(np.abs(contour1_stand(d, "grid") - r["q"]).max()))
        contour1_full(d); ts = []
        for _ in range(3):
            t = time.perf_counter(); q, kind, state = contour1_full(d); ts.append(time.perf_counter() - t)
        r["q"] = q; r["kind"] = kind; r["state"] = state; r["t_c1"] = float(np.median(ts))
    pickle.dump(recs, open(f"{outdir}/{split}_{ch}.pkl", "wb"))
    print(split, ch, "ok", flush=True)
print("макс. відхилення відтвореного q старого стенду від збереженого:", maxdev)
