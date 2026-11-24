"""Додаткові перевірки: (1) чесне налаштування порогу аналога S4 за рівної точності;
(2) модельний сценарій зі швидшим детектором (лише заміна часу детектора, вибір маршрутів — виміряний)."""
import numpy as np, sys
sys.argv = ['analyze.py', '0.10', 'quick']
exec(open('analyze.py').read().split("# бутстреп-інтервали")[0])
# (1) S4: поріг, що мінімізує час за умови mAP >= mAP методу S5 на навчальній вибірці
ch5_tr = clf_min.predict(Xtr); ap5_tr = pooled(tr, ch5_tr)
best = None
for tau in np.linspace(-0.5, 2.5, 61):
    ch = [mod if r['routes']['R0_none']['max_score'] < tau else 0 for r in tr]
    a = pooled(tr, ch)
    t = np.mean([r['routes']['R0_none']['t_det'] + ((r['routes'][RN[mod]]['t_route'] + r['routes'][RN[mod]]['t_det']) if c else 0) for r, c in zip(tr, ch)])
    if a >= ap5_tr and (best is None or t < best[1]): best = (tau, t, a)
print(f'S5 train mAP={ap5_tr:.3f}; S4 tau за рівної точності: {best}')
if best:
    tau = best[0]; ch = []; tm = []
    for r in te:
        trig = r['routes']['R0_none']['max_score'] < tau; c = mod if trig else 0
        ch.append(c); tm.append(r['routes']['R0_none']['t_det'] + ((r['routes'][RN[mod]]['t_route'] + r['routes'][RN[mod]]['t_det']) if trig else 0))
    tm = np.array(tm); print(f'S4* test: mAP={pooled(te, ch):.3f} FPS={1/tm.mean():.2f} trig={np.mean([c!=0 for c in ch]):.2f}')
# (2) модельний сценарій: детектор у k разів швидший (наприклад, GPU), маршрути — на CPU як виміряно
for k in [1, 3, 9]:
    out = {}
    for nm in ['S3 макс. точність', 'S5 запропонований']:
        ch, tm = strategy(nm, te)
        tm2 = np.array([t - te[i]['routes'][RN[c]]['t_det'] * (1 - 1 / k) for i, (c, t) in enumerate(zip(ch, tm))])
        out[nm] = 1 / tm2.mean()
    print(f'детектор у {k} разів швидший: FPS S3={out["S3 макс. точність"]:.2f}, S5={out["S5 запропонований"]:.2f}, приріст {(out["S5 запропонований"]/out["S3 макс. точність"]-1)*100:.1f} %')
