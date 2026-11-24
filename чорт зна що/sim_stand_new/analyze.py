"""Аналіз: еталонні маршрути, навчання селектора, порівняння стратегій за однакових умов."""
import numpy as np, pickle, time, sys, json
from sklearn.tree import DecisionTreeClassifier
from common import ap_from_matches, ROUTE_NAMES
EPS = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
import glob
tr = sum([pickle.load(open(f, 'rb')) for f in sorted(glob.glob('train_*.pkl'))], [])
te = sum([pickle.load(open(f, 'rb')) for f in sorted(glob.glob('test_*.pkl'))], [])
print('train', len(tr), 'test', len(te))
RN = ROUTE_NAMES; K = len(RN)

def Q(r, rn): return ap_from_matches(r['routes'][rn]['matches'], r['n_gt'])       # покадрова AP@0.5
# вартість маршруту C(R): медіана виміряного часу маршруту на навчальній вибірці
C = np.array([np.median([r['routes'][rn]['t_route'] for r in tr]) for rn in RN])

def labels(recs, eps):
    lab_min, lab_max = [], []
    for r in recs:
        q = np.array([Q(r, rn) for rn in RN]); qmax = q.max()
        suff = np.where(q >= qmax - eps)[0];  lab_min.append(suff[np.argmin(C[suff])])     # критерій методу
        best = np.where(q == qmax)[0];        lab_max.append(best[np.argmin(C[best])])     # макс. точність, нічия -> дешевший
    return np.array(lab_min), np.array(lab_max)

Xtr = np.array([r['q'] for r in tr]); Xte = np.array([r['q'] for r in te])
ytr_min, ytr_max = labels(tr, EPS); yte_min, yte_max = labels(te, EPS)
clf_min = DecisionTreeClassifier(max_depth=6, min_samples_leaf=5, random_state=0).fit(Xtr, ytr_min)
clf_max = DecisionTreeClassifier(max_depth=6, min_samples_leaf=5, random_state=0).fit(Xtr, ytr_max)
ts = []
for i in range(300):
    t = time.perf_counter(); clf_min.predict(Xte[i % len(Xte)][None]); ts.append(time.perf_counter() - t)
t_sel = float(np.median(ts))

KIND_ROUTE = {"blur": "R4_unsharp", "noise": "R6_nlm", "under": "R1_gamma",
              "over": "R2_clahe", "mixed": "R2_clahe", "contrast": "R2_clahe"}
def rule(r):
    if r["state"] != "repair":
        return RN.index("R0_none")
    return RN.index(KIND_ROUTE[r["kind"]])

heavy = int(np.argmax(C))
# аналог «обробка за порогом упевненості детектора»: модуль — найкращий за навчальною mAP маршрут,
# поріг підібрано на навчальній вибірці для максимуму mAP (вигідні для аналога умови)
def pooled(recs, choice): 
    m = []; n = 0
    for r, c in zip(recs, choice): m += r['routes'][RN[c]]['matches']; n += r['n_gt']
    return ap_from_matches(m, n)
mod = max(range(1, K), key=lambda k: pooled(tr, [k] * len(tr)))
best_tau, best_ap = None, -1
for tau in np.linspace(-0.5, 2.0, 26):
    ch = [mod if r['routes']['R0_none']['max_score'] < tau else 0 for r in tr]
    a = pooled(tr, ch)
    if a > best_ap: best_ap, best_tau = a, tau

def strategy(name, recs):
    ch, tm = [], []
    for i, r in enumerate(recs):
        R = r['routes']
        if name == 'S0 без передобробки':   c = 0; t = R[RN[0]]['t_det']
        elif name == 'S1 найдорожчий маршрут': c = heavy; t = R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        elif name == 'S2 тип -> фільтр':       c = rule(r); t = r['t_c1'] + R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        elif name == 'S3 макс. точність':      c = int(clf_max.predict(r['q'][None])[0]); t = r['t_c1'] + t_sel + R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        elif name == 'S4 поріг упевненості':
            trig = R['R0_none']['max_score'] < best_tau; c = mod if trig else 0
            t = R['R0_none']['t_det'] + (R[RN[mod]]['t_route'] + R[RN[mod]]['t_det'] if trig else 0)
        elif name == 'S5 запропонований':      c = int(clf_min.predict(r['q'][None])[0]); t = r['t_c1'] + t_sel + R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        elif name == 'O3 еталон макс.':        c = yte_max[i]; t = R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        elif name == 'O5 еталон мін. достатн.': c = yte_min[i]; t = R[RN[c]]['t_route'] + R[RN[c]]['t_det']
        ch.append(c); tm.append(t)
    return np.array(ch), np.array(tm)

names = ['S0 без передобробки', 'S1 найдорожчий маршрут', 'S2 тип -> фільтр', 'S3 макс. точність',
         'S4 поріг упевненості', 'S5 запропонований', 'O3 еталон макс.', 'O5 еталон мін. достатн.']
res = {}
for nm in names:
    ch, tm = strategy(nm, te)
    res[nm] = dict(ch=ch, tm=tm, ap=pooled(te, ch), ms=tm.mean() * 1000, fps=1 / tm.mean())
print(f'eps={EPS}  t_sel={t_sel*1e3:.3f} ms  t_c1={np.median([r["t_c1"] for r in te])*1e3:.2f} ms  '
      f'heavy={RN[heavy]}  S4 module={RN[mod]} tau={best_tau:.2f}')
print('C(R), ms:', ', '.join(f'{RN[k]}={C[k]*1e3:.2f}' for k in range(K)))
print(f'{"стратегія":26s} {"mAP@0.5":>8s} {"мс/кадр":>8s} {"FPS":>7s}  частки маршрутів')
for nm in names:
    v = res[nm]; sh = np.bincount(v['ch'], minlength=K) / len(v['ch'])
    print(f'{nm:26s} {v["ap"]:8.3f} {v["ms"]:8.1f} {v["fps"]:7.2f}  ' + ' '.join(f'{RN[k][:2]}:{sh[k]:.2f}' for k in range(K) if sh[k] > 0))

# бутстреп-інтервали для пропусків у новизні
def boot(a, b, B=1000, seed=0):
    rng = np.random.default_rng(seed); n = len(te); g, d = [], []
    A, Bc = res[a], res[b]
    for _ in range(B):
        idx = rng.integers(0, n, n); recs = [te[i] for i in idx]
        fa = 1 / A['tm'][idx].mean(); fb = 1 / Bc['tm'][idx].mean()
        g.append((fa / fb - 1) * 100)
        d.append((pooled(recs, Bc['ch'][idx]) - pooled(recs, A['ch'][idx])) * 100)
    return np.percentile(g, [2.5, 50, 97.5]), np.percentile(d, [2.5, 50, 97.5])
REFS = ['S3 макс. точність', 'S1 найдорожчий маршрут', 'S4 поріг упевненості', 'S2 тип -> фільтр', 'S0 без передобробки'] if (len(sys.argv) < 3 or sys.argv[2] != 'quick') else ['S3 макс. точність']
for ref in REFS:
    A, B = res['S5 запропонований'], res[ref]
    g, d = boot('S5 запропонований', ref)
    print(f'S5 vs {ref}: FPS +{(A["fps"]/B["fps"]-1)*100:.1f} % [95% ДІ {g[0]:.1f}; {g[2]:.1f}], '
          f'зниження mAP {(B["ap"]-A["ap"])*100:.2f} п.п. [95% ДІ {d[0]:.2f}; {d[2]:.2f}], '
          f'відносне {(B["ap"]-A["ap"])/B["ap"]*100:.2f} %')
