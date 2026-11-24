"""95 % ДІ для порівняння S5 з аналогом S4 за рівної точності (eps = 0.05).
Поріг S4 добирається так, щоб mAP S4 >= mAP S5 за максимальної FPS S4:
(i) один раз на повній тестовій вибірці; (ii) заново в кожній бутстреп-вибірці."""
import numpy as np, sys
sys.argv = ['analyze.py', '0.05', 'quick']
g = {}
src = open('analyze.py').read()
exec(src.split("names = [")[0], g)
exec("names = [" + src.split("names = [")[1].split("# бутстреп-інтервали")[0], g)
te, RN, mod, ap_from_matches, res = g['te'], g['RN'], g['mod'], g['ap_from_matches'], g['res']
n = len(te); taus = np.linspace(-0.5, 2.5, 121)
ch5 = res['S5 запропонований']['ch']; tm5 = res['S5 запропонований']['tm']
ms0 = np.array([r['routes']['R0_none']['max_score'] for r in te])
t0 = np.array([r['routes']['R0_none']['t_det'] for r in te])
tM = np.array([r['routes'][RN[mod]]['t_route'] + r['routes'][RN[mod]]['t_det'] for r in te])
m0 = [r['routes']['R0_none']['matches'] for r in te]; mM = [r['routes'][RN[mod]]['matches'] for r in te]
m5 = [te[i]['routes'][RN[ch5[i]]]['matches'] for i in range(n)]; ngt = np.array([r['n_gt'] for r in te])
def pooled(idx, trig=None):
    m = []
    for i in idx: m += (mM[i] if (trig is not None and trig[i]) else (m5[i] if trig is None else m0[i]))
    return ap_from_matches(m, ngt[idx].sum())
def s4_equal(idx):
    a5 = pooled(idx); best = None
    for tau in taus:
        trig = ms0 < tau; a = pooled(idx, trig); t = (t0[idx] + trig[idx] * tM[idx]).mean()
        if a >= a5 and (best is None or t < best[1]): best = (tau, t, a)
    if best is None:   # S4 не досягає точності S5 за жодного порогу: беремо найточніше налаштування S4 (найвигідніше для аналога)
        cand = []
        for tau in taus:
            trig = ms0 < tau; cand.append((pooled(idx, trig), -(t0[idx] + trig[idx] * tM[idx]).mean(), tau))
        a, mt, tau = max(cand); return (tau, -mt, a, 'unreached'), a5
    return best + ('ok',), a5
full = np.arange(n); (tau_f, t_f, a_f, _), a5 = s4_equal(full)
print(f'повна вибірка: tau={tau_f:.3f}, S4 FPS={1/t_f:.2f}, mAP={a_f:.3f}; S5 FPS={1/tm5.mean():.2f}, mAP={a5:.3f}; '
      f'перевага {(1/tm5.mean())/(1/t_f)*100-100:.1f} %; частка повторних детекцій {(ms0 < tau_f).mean():.3f}')
rng = np.random.default_rng(0); gi, gr, da, unr = [], [], [], 0
for b in range(1000):
    idx = rng.integers(0, n, n)
    fps5 = 1 / tm5[idx].mean()
    trig = ms0 < tau_f
    gi.append((fps5 / (1 / (t0[idx] + trig[idx] * tM[idx]).mean()) - 1) * 100)
    da.append((pooled(idx, trig) - pooled(idx)) * 100)
    best, _ = s4_equal(idx); unr += best[3] == 'unreached'
    gr.append((fps5 / (1 / best[1]) - 1) * 100)
p = lambda v: np.percentile(v, [2.5, 97.5])
print(f'(i) поріг фіксований: перевага FPS 95% ДІ [{p(gi)[0]:.1f}; {p(gi)[1]:.1f}] %, різниця mAP (S4−S5) [{p(da)[0]:.2f}; {p(da)[1]:.2f}] п.п.')
print(f'(ii) поріг заново в кожній вибірці: перевага FPS 95% ДІ [{p(gr)[0]:.1f}; {p(gr)[1]:.1f}] %, медіана {np.median(gr):.1f} %; вибірок, де S4 не досягає точності S5: {unr}/1000')
