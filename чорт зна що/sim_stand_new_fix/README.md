# Стенд new_fix: Контур 1 (нова C-версія) після зауважень

База: `contour_1` → `c/contour_1_new_fix`. Оригінальний `sim_stand_new` не змінюється.

Що змінено щодо зауважень:
- вектор `(d_u, d_o, d_c, d_n, d_b)` з C (`c1lib.assess`); тип/стан лише в журналі;
- `s_L0` / `n0` підібрані на навчальній сітці; відносна плоска маска шуму;
- у `ROUTES` додані власні C-маршрути `C1_gamma`, `C2_clahe`, `C3_stretch`, `C4_median`, `C5_deblur`;
- S5 — дерево рішень на еталонних маршрутах (ε = 0.05), без ручного «OK → не обробляти».

Потрібно: Python 3, numpy, opencv-python, scikit-learn; зібрана `c/contour_1_new_fix/bin/contour_1.dll`.

```
python collect.py train 100 1001 0
python collect.py train 100 1002 1
python collect.py train 100 1003 2
python collect.py train 100 1004 3
python collect.py test 100 2001 0
python collect.py test 75 2002 1
python collect.py test 75 2003 2
set PYTHONUTF8=1
python analyze.py 0.05
python ci_s4.py
```

Додатково: `python fit_blur.py check` — таблиці `d_b(L)`, `d_n(σ)`.
На Windows для `ci_s4.py` потрібен `PYTHONUTF8=1`.
