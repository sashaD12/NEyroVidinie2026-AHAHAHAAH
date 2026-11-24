"""Підбір s_L0 (і n0) на навчальній вибірці та перевірка, що d_b зростає з довжиною змазування L.
Кадри відтворюються з тих самих зерен, що й у collect.py (лише навчальні частини).
python fit_blur.py fit   — підбір за формулами з виміряних C-кодом s_L, n_flat
python fit_blur.py check — таблиці d_b і d_n за значеннями, які повертає зібрана C-бібліотека"""
import sys
import warnings

import numpy as np
from scipy.stats import spearmanr

import c1lib
from common import make_scene, degrade, EXPOSURE, NOISE, BLUR

warnings.filterwarnings("ignore")
TRAIN_CHUNKS = [(100, 1001), (100, 1002), (100, 1003), (100, 1004)]
VERSION = "new"
ORIGINAL = dict(s_L0=4500.0, n0=3.8)
mode = sys.argv[1] if len(sys.argv) > 1 else "fit"


def train_frames():
    for n, seed in TRAIN_CHUNKS:
        rng = np.random.default_rng(seed)
        for _ in range(n):
            img, _boxes = make_scene(rng)
            e, s, L = rng.choice(EXPOSURE), rng.choice(NOISE), rng.choice(BLUR)
            yield e, s, L, degrade(img, e, s, L, rng)


def d_b_formula(s_l, d_motion, s_l0):
    if VERSION == "old":
        return np.clip(1.0 - s_l / s_l0, 0.0, 1.0)
    d_iso = np.clip(1.0 - np.log1p(s_l) / np.log1p(s_l0), 0.0, 1.0)
    return np.maximum(d_iso, d_motion)


def d_n_formula(n_flat, d_motion, s_l_raw, n0):
    if VERSION == "old":
        return np.clip(n_flat / n0, 0.0, 1.0)
    d = np.clip((n_flat - 1.35) / n0, 0.0, 1.0)
    d = np.where(d_motion >= 0.35, d * 0.25, d)
    return np.where(s_l_raw > 8000.0, d * np.clip(12000.0 / np.maximum(s_l_raw, 1e-6), 0.0, 1.0), d)


def rho(x, y):
    v = spearmanr(x, y).correlation
    return -1.0 if np.isnan(v) else float(v)


def fit_scale(values, levels, formula, extra_grid):
    grid = np.unique(np.concatenate([np.quantile(values, np.linspace(0.005, 1.0, 400)), extra_grid]))
    grid = grid[grid > 0]
    rhos = np.array([rho(formula(g), levels) for g in grid])
    best = rhos.max()
    return float(grid[np.where(rhos >= best - 1e-4)[0][0]]), best


rows = []
for e, s, L, d in train_frames():
    q, dg = c1lib.assess(d)
    rows.append((e, s, L, dg[0], dg[12], dg[5], dg[1], q[3], q[4]))
R = np.array(rows, np.float64)
E, S, LL, SL, SLRAW, DM, NF, DN, DB = R.T
cfg = c1lib.config()
print(f"версія={VERSION}  кадрів={len(R)}  конфіг C: {cfg}")


def table(db, title, levels, level_name, value_name):
    print(title)
    print(f"{level_name:>5s} {'n':>4s} {'сер.':>7s} {'медіана':>8s} {'=0':>6s} {'=1':>6s}")
    for lv in levels:
        m = (LL if level_name == "L" else S) == lv
        print(f"{lv:5d} {m.sum():4d} {db[m].mean():7.3f} {np.median(db[m]):8.3f} {(db[m] <= 0).mean():6.2f} {(db[m] >= 1).mean():6.2f}")
    other = NOISE if level_name == "L" else BLUR
    other_arr = S if level_name == "L" else LL
    main_arr = LL if level_name == "L" else S
    other_name = "sigma" if level_name == "L" else "L"
    print(f"середнє {value_name}: рядки — {other_name}, стовпці — {level_name}")
    print(f"{other_name:>5s} " + " ".join(f"{lv:>7d}" for lv in levels))
    for o in other:
        print(f"{o:5d} " + " ".join(f"{db[(other_arr == o) & (main_arr == lv)].mean():7.3f}" for lv in levels))
    per = [rho(db[other_arr == o], main_arr[other_arr == o]) for o in other]
    print(f"rho Спірмена({value_name}, {level_name}) = {rho(db, main_arr):.3f}; за {other_name} {other}: " + ", ".join(f"{v:.3f}" for v in per))


def calib(values, arr, lo_level, mid_level, hi_level):
    tau = 0.5 * (np.median(values[arr == lo_level]) + np.median(values[arr == mid_level]))
    t = max(np.median(values[arr == hi_level]), tau + 0.05)
    return float(tau), float(t)


if mode == "fit":
    print("\nA. Як було: s_L = дисперсія Лапласіана на прорідженій сітці")
    print(f"   s_L: медіана {np.median(SLRAW):.1f}, 99 % {np.quantile(SLRAW, 0.99):.1f}, макс {SLRAW.max():.1f}")
    for s0 in [100.0, ORIGINAL["s_L0"]]:
        db = d_b_formula(SLRAW, DM, s0)
        print(f"   s_L0={s0:8.1f}: rho(d_b, L)={rho(db, LL):.3f}, частка d_b=0: {(db <= 0).mean():.3f}")
    s_raw, r_raw = fit_scale(SLRAW, LL, lambda g: d_b_formula(SLRAW, DM, g), SLRAW.max() * np.geomspace(1, 4, 20))
    print(f"   найкраще s_L0 на сирому s_L = {s_raw:.1f}: rho = {r_raw:.3f} — d_b за підбору s_L0 з L не зростає")
    for s in NOISE:
        print(f"   sigma={s:2d}: медіана сирого s_L за L {BLUR}: " + ", ".join(f"{np.median(SLRAW[(S == s) & (LL == L)]):.0f}" for L in BLUR))

    print("\nB. Стало: s_L = (D[Лапласіан блочних середніх] − 20·sigma_n²/(b_x·b_y)) / D[блочних середніх]")
    s_l0, r_b = fit_scale(SL, LL, lambda g: d_b_formula(SL, DM, g), SL.max() * np.geomspace(1, 4, 20))
    print("   критерій: максимум rho Спірмена між d_b і L; за рівних — найменше s_L0 (ширший діапазон d_b)")
    print(f"   ПІДІБРАНО s_L0 = {s_l0:.4f} (rho = {r_b:.3f})")
    db_fit = d_b_formula(SL, DM, s_l0)
    table(db_fit, f"\n   d_b після підбору (s_L0 = {s_l0:.4f}):", BLUR, "L", "d_b")

    print("\nC. Шум: відносна маска, n0 за тим самим правилом (rho Спірмена між d_n і sigma)")
    for n0 in [ORIGINAL["n0"]]:
        dn = d_n_formula(NF, DM, SLRAW, n0)
        print(f"   n0={n0:.2f} (як було): rho(d_n, sigma) = {rho(dn, S):.3f}, частка d_n=1: {(dn >= 1).mean():.3f}")
    n0, r_n = fit_scale(NF, S, lambda g: d_n_formula(NF, DM, SLRAW, g), NF.max() * np.geomspace(1, 4, 20))
    print(f"   ПІДІБРАНО n0 = {n0:.4f} (rho = {r_n:.3f})")
    dn_fit = d_n_formula(NF, DM, SLRAW, n0)
    table(dn_fit, f"\n   d_n після підбору (n0 = {n0:.4f}):", NOISE, "sigma", "d_n")

    tau_b, t_b = calib(db_fit, LL, 0, 5, 15)
    tau_n, t_n = calib(dn_fit, S, 0, 5, 20)
    print("\nD. Пороги журналу типу (лише журнал і базова стратегія S2), за медіанами навчальної вибірки:")
    print(f"   tau_b = (med d_b|L=0 + med d_b|L=5)/2 = {tau_b:.4f}, t_b = med d_b|L=15 = {t_b:.4f}")
    print(f"   tau_n = (med d_n|s=0 + med d_n|s=5)/2 = {tau_n:.4f}, t_n = med d_n|s=20 = {t_n:.4f}")
    print(f"\nДЛЯ config.c: s_L0={s_l0:.4f}f n0={n0:.4f}f tau_b={tau_b:.4f}f t_b={t_b:.4f}f tau_n={tau_n:.4f}f t_n={t_n:.4f}f")
else:
    table(DB, f"\nd_b з C-бібліотеки (s_L0 = {cfg['s_L0']:.4f}):", BLUR, "L", "d_b")
    table(DN, f"\nd_n з C-бібліотеки (n0 = {cfg['n0']:.4f}, частка точок {cfg['flat_frac']:.2f}):", NOISE, "sigma", "d_n")
