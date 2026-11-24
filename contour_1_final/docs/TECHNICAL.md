# Технічна документація: Контур 1 (final / new_fix)

Версія: фінальна C-реалізація другої лінії Контуру 1 після зауважень рецензента.  
Каталог коду: `contour_1_final/` (корінь проєкту NEyroVidinie).  
Стенд, на якому знято числа: `чорт зна що/sim_stand_new_fix/`.

---

## 1. Призначення

Контур 1 оцінює стан напівтонового кадру (експозиція, контраст, шум, розмиття) і обирає **мінімально достатній** маршрут передобробки **до** запуску детектора.

Конвеєр кадру:

1. `ad_assess_frame` — вектор стану \(q = (d_u, d_o, d_c, d_n, d_b)\);
2. `ad_select_route` — навчене дерево рішень на \(q\);
3. `ad_apply_route` — застосування обраного фільтра (або нічого).

Тип дефекту (`log_kind`) і стан (`log_state`) **не керують** обробкою: вони лише для журналу / стратегії S2 на стенді. Рішення «без обробки» приймає тільки селектор (`AD_ROUTE_NONE`).

---

## 2. Структура модулів

| Файл | Роль |
|---|---|
| `include/adaptive.h` | публічні типи й API |
| `src/assess.c` | оцінка кадру, вектор \(q\) |
| `src/config.c` | пороги за замовчуванням |
| `src/select.c` | обхід дерева рішень |
| `src/selector_tree.c` | вузли навченого дерева |
| `src/routes.c` | фільтри маршрутів |
| `src/pipeline.c` | assess → select → apply |
| `src/io_stb.c` | завантаження/збереження PNG/JPEG/BMP |
| `src/pyapi.c` | ctypes API для стенду |
| `apps/ad_enhance.c` | CLI |
| `tests/test_assess.c` | unit/регресійні тести |
| `third_party/` | stb_image / stb_image_write |

---

## 3. Публічний API (приклад)

```c
#include "adaptive.h"

AdFrame frame;
AdConfig cfg;
AdProcessResult result;
uint8_t* owned = 0;

ad_config_default(&cfg);
ad_load_gray("frame.jpg", &frame, &owned);
result = ad_process_frame(&frame, &cfg);

printf("q = %.3f %.3f %.3f %.3f %.3f\n",
  result.assess.v[AD_V_U],
  result.assess.v[AD_V_O],
  result.assess.v[AD_V_C],
  result.assess.v[AD_V_N],
  result.assess.v[AD_V_B]);
printf("route=%s applied=%d\n",
  ad_route_name(result.route), result.applied);

ad_save_gray("out.png", &frame);
ad_free_owned(owned);
```

Окремі кроки:

```c
AdAssess a;
AdRoute r;
ad_assess_frame(&frame, &cfg, &a);
r = ad_select_route(a.v);
if (r != AD_ROUTE_NONE) {
  ad_apply_route(&frame, r, a.v, &cfg);
}
```

Вектор індексується так:

```c
typedef enum AdVecIndex {
  AD_V_U = 0,  /* underexposure */
  AD_V_O = 1,  /* overexposure */
  AD_V_C = 2,  /* low contrast */
  AD_V_N = 3,  /* noise */
  AD_V_B = 4   /* blur / motion */
} AdVecIndex;
```

---

## 4. Сітка оцінювання

Кадр проріджується до сітки \(160 \times 120\) вузлів:

\[
\Delta x = \left\lfloor \frac{W}{160} \right\rfloor,\quad
\Delta y = \left\lfloor \frac{H}{120} \right\rfloor.
\]

Координати вузлів обмежено \([1; W-2]\), \([1; H-2]\), щоб завжди були сусіди для градієнта та Лапласіана.  
Усі \(d_u, d_o, d_c\) і гістограма — лише по вузлах сітки. Шум і анізотропія використовують **повнороздільні** сусіди вузлів.

Для кадру \(640\times360\): \(\Delta x=4\), \(\Delta y=3\), \(N = 19200\).

---

## 5. Освітленість і контраст

Нехай \(g\) — яскравості вузлів, \(N\) — їх кількість.

\[
\mu = \frac{1}{N}\sum g,\qquad
\sigma = \sqrt{\max(\mathrm{Var}(g), 0)}.
\]

Частки:

\[
p_b = \frac{|\{g\le 10\}|}{N},\quad
p_s = \frac{|\{g\ge 245\}|}{N},\quad
p_{\mathrm{dark}} = \frac{|\{g\le 55\}|}{N}.
\]

Показники (усі далі \(\mathrm{clamp01}(x)=\min(1,\max(0,x))\)):

\[
\begin{aligned}
d_u &= \mathrm{clamp01}\Big(\max\Big(\frac{\mu_0-\mu}{\mu_0},\ \frac{p_b}{p_{\max}},\ \frac{p_{\mathrm{dark}}}{0.75}\Big)\Big),\\
d_o &= \mathrm{clamp01}\Big(\max\Big(\frac{\mu-\mu_1}{255-\mu_1},\ \frac{p_s}{p_{\max}}\Big)\Big),\\
d_c &= \mathrm{clamp01}\Big(1 - \frac{\sigma}{\sigma_0}\Big).
\end{aligned}
\]

Константи за замовчуванням (`config.c`):

| Символ | Значення | Зміст |
|---|---:|---|
| \(\mu_0\) | 80 | межа «темно» |
| \(\mu_1\) | 180 | межа «світло» |
| \(\sigma_0\) | 40 | еталонний контраст |
| \(p_{\max}\) | 0.5 | нормування хвостів гістограми |

Фрагмент з `assess.c` (логіка відповідає формулам вище):

```c
du = clamp(max((mu0 - mu) / mu0, pb / pmax, pdark / 0.75));
do_ = clamp(max((mu - mu1) / (255 - mu1), ps / pmax));
dc = clamp(1 - sig / sigma0);
```

---

## 6. Розмиття \(d_b\)

\[
d_b = \max(d_{\mathrm{iso}},\ d_{\mathrm{motion}}).
\]

### 6.1. Ізотропна різкість (block sharpness)

1. Оцінка шуму сенсора (Immerkær-подібна маска \(3\times3\) на вузлах):

\[
\hat\sigma_n = \frac{1.2533141}{6}\cdot\frac{1}{N}\sum |I * M|.
\]

2. Середні по блоках \(b_x\times b_y\) навколо вузлів сітки → масив \(B[i,j]\).

3. Дисперсія Лапласіана на \(B\) з відніманням шуму:

\[
s_L = \frac{\max\big(\mathrm{Var}(L(B)) - 20\,\hat\sigma_n^2/(b_x b_y),\ 0\big)}{\max(\mathrm{Var}(B),\ 1)}.
\]

4. Логарифмічна нормалізація (підібране \(s_{L0}=0.3345\)):

\[
d_{\mathrm{iso}} = \mathrm{clamp01}\Big(1 - \frac{\ln(1+s_L)}{\ln(1+s_{L0})}\Big).
\]

Чому не «сирий» Лапласіан на сітці: при \(s_{L0}=100\) або \(4500\) на дисперсії вузлів \(d_b\) майже завжди 0 або майже сталий. Block sharpness робить \(d_b\) монотонним за довжиною змазування \(L\) (на навчальній сітці стенду \(\rho_{\mathrm{Spearman}}(d_b,L)\approx 0.69\)).

### 6.2. Складова змазування (анізотропія)

\[
e_x = \overline{|I_x|},\quad e_y = \overline{|I_y|},\quad
a = \frac{\max(e_x,e_y)}{\max(\min(e_x,e_y), 0.5)}.
\]

\[
d_{\mathrm{motion}} =
\begin{cases}
\mathrm{clamp01}\big((a-1.45)/1.55\big), & a>1.45\ \land\ \max(e_x,e_y)>1.8,\\
0, & \text{інакше}.
\end{cases}
\]

```c
d_iso = clamp01(1.0f - (log1pf(s_L) / log1pf(cfg->s_L0)));
if (aniso > 1.45f && e_max > 1.8f) {
  d_motion = clamp01((aniso - 1.45f) / 1.55f);
}
d_b = fmaxf(d_iso, d_motion);
```

---

## 7. Шум \(d_n\) (відносна плоска маска)

Зауваження вимагало замінити абсолютний поріг \(|\nabla I|<\tau_e\) на **частку** точок із найменшим градієнтом.

1. На кожному вузлі:

\[
|\nabla I| = |I(x+1,y)-I(x-1,y)| + |I(y+1)-I(y-1)|,
\]
\[
r = \big|I - \bar I_{3\times3}\big|.
\]

2. Береться \(k = \mathrm{round}(f\cdot N)\) точок з найменшим \(|\nabla I|\), \(f=\texttt{flat\_frac}=0.10\).  
   Якщо валідних точок немає → \(n_{\mathrm{flat}}=0\), \(d_n=0\).

3.

\[
n_{\mathrm{flat}} = \frac{1}{k}\sum_{i\in\mathrm{Flat}} r_i,\qquad
d_n = \mathrm{clamp01}\big((n_{\mathrm{flat}}-1.35)/n_0\big),\quad n_0=7.158.
\]

4. Послаблення:

- якщо \(d_{\mathrm{motion}}\ge 0.35\) → \(d_n \leftarrow 0.25\,d_n\);
- якщо сира дисперсія Лапласіана сітки \(s_{L,\mathrm{raw}}>8000\) → \(d_n \leftarrow d_n\cdot\mathrm{clamp01}(12000/s_{L,\mathrm{raw}})\).

```c
n_flat = ad_flat_residual(grad_buf, resid_buf, grad_n, cfg->flat_frac, &flat_used);
if (flat_used > 0 && cfg->n0 > 0.0f) {
  d_n = clamp01((n_flat - 1.35f) / cfg->n0);
}
```

---

## 8. Журнал типу / стану (не для рішення)

Тяжкість:

\[
s(d;\tau,t) =
\begin{cases}
0, & d\le\tau,\\
1, & d\ge t,\\
(d-\tau)/(t-\tau), & \text{інакше}.
\end{cases}
\]

Пороги журналу (після калібрування на train):  
\(\tau_l=0.48,\ t_l=0.90,\ \tau_n=0.242,\ t_n=1,\ \tau_b=0.1805,\ t_b=0.7071\).

Тип = дефект із найбільшою тяжкістю серед blur / noise / light.  
Стан `ok` / `repair` / `bad` пишеться в `log_state`, але **pipeline його ігнорує**.

---

## 9. Селектор маршруту

Маршрути:

| Enum | Ім'я | Операція |
|---|---|---|
| 0 | `NONE` | без змін |
| 1 | `GAMMA` | м’яка гамма за \(d_u\) |
| 2 | `CLAHE` | CLAHE, clip від сили світла |
| 3 | `STRETCH` | розтяг гістограми (перцентилі) |
| 4 | `MEDIAN` | медіана \(3\times3\) |
| 5 | `DEBLUR` | ітеративний деблюр (Ван Циттерт) + unsharp |

Селектор — бінарне дерево рішень на ознаках \(q_0\ldots q_4\). Обхід:

```c
AdRoute ad_select_route(const float* v) {
  uint32_t node = 0;
  while (ad_tree_nodes[node].left >= 0) {
    const AdTreeNode* t = &ad_tree_nodes[node];
    if ((double)v[t->feature] <= t->threshold) {
      node = (uint32_t)t->left;
    } else {
      node = (uint32_t)t->right;
    }
  }
  return (AdRoute)ad_tree_nodes[node].route;
}
```

Дерево експортоване в `selector_tree.c`. На стенді стратегія **S5** навчає аналогічне дерево на **еталонних** маршрутах за критерієм мінімальної вартості серед маршрутів з AP ≥ max AP − ε (ε = 0.05). У C-бібліотеці лежить компактне дерево, навчене на синтетиці з тим самим ε-критерієм по проксі якості \(\max(q)\) після маршруту (швидкий сурогат до повного HOG+SVM).

Важливо: немає правила «якщо OK — не чіпати». `NONE` з’являється лише як лист дерева.

---

## 10. Фільтри (`routes.c`)

### GAMMA

\[
\gamma = \mathrm{clamp}(1 - 0.22\,d_u,\ 0.70,\ 0.92),\qquad
I'(x) = 255\cdot\big(I/255\big)^{\gamma}.
\]

### CLAHE

Clip limit:

\[
c = \mathrm{clamp}(c_{\min} + 0.6\,c_{\mathrm{span}}\cdot d_L,\ 1.8,\ 3.5),
\]
де \(d_L=\max(d_u,d_o,d_c)\), сітка тайлів \(8\times8\).

### STRETCH

Лінійне розтягнення між перцентилями гістограми кадру.

### MEDIAN

Медіанний фільтр \(3\times3\).

### DEBLUR (Ван Циттерт уздовж осі смазу)

Оцінюється домінантна вісь градієнта. Далі \(N_{\mathrm{iter}}=6+\lfloor 6r\rfloor\) ітерацій (обмежено 14), радіус \(3+\lfloor 4r\rfloor\) (обмежено 8), \(r=d_b\):

\[
x_{k+1} = x_k + \lambda\,(y - H x_k),\quad \lambda = 0.42 + 0.18 r,
\]

де \(H\) — box-blur уздовж осі. Після ітерацій — легке нерізке маскування.

```c
if (route == AD_ROUTE_GAMMA) {
  ad_build_gamma_lut(clamp(1.0f - 0.22f * v[AD_V_U], 0.70f, 0.92f), lut);
  ad_apply_lut(frame, lut);
}
```

---

## 11. Конвеєр і час

```c
t0 = ad_now_s();
ad_assess_frame(frame, cfg, &result.assess);
t1 = ad_now_s();
result.route = ad_select_route(result.assess.v);
t2 = ad_now_s();
if (result.route != AD_ROUTE_NONE) {
  ad_apply_route(frame, result.route, result.assess.v, cfg);
  result.applied = 1;
}
t3 = ad_now_s();
```

Час кадру на стенді для S5:

\[
t = t_{c1} + t_{\mathrm{sel}} + t_r(R) + t_d(R).
\]

---

## 12. Параметри за замовчуванням

З `config.c`:

| Параметр | Значення |
|---|---:|
| `s_L0` | 0.3345 |
| `n0` | 7.1580 |
| `flat_frac` | 0.10 |
| `tau_l`, `t_l` | 0.48, 0.90 |
| `tau_n`, `t_n` | 0.242, 1.00 |
| `tau_b`, `t_b` | 0.1805, 0.7071 |
| CLAHE clip min/span | 2.0 / 6.0 |
| CLAHE tiles | 8×8 |

`s_L0` і `n0` підібрані на навчальній вибірці стенду максимізацією \(\rho_{\mathrm{Spearman}}\) між \(d_b\) і \(L\), між \(d_n\) і \(\sigma\).

---

## 13. Зв’язок зі стендом

Стенд `sim_stand_new_fix` викликає DLL через `c1lib.py` (`ad_py_assess`, `ad_py_route`, `ad_py_select`).

У `ROUTES` додані власні C-маршрути з виміряною вартістю \(C(R)\) (медіана часу на train):

| Маршрут | \(C(R)\), мс |
|---|---:|
| C1_gamma | 0.23 |
| C2_clahe | 2.41 |
| C3_stretch | 0.27 |
| C4_median | 47.75 |
| C5_deblur | 56.16 |

Плюс базові OpenCV R0–R7 для порівняння стратегій.

---

## 14. Результати тестування (фінальний стенд)

Тест: 250 кадрів, ε = 0.05. Джерела: `docs/results/analyze_out.txt`, `ci_s4_out.txt`.

### Стратегії

| Стратегія | mAP@0.5 | мс/кадр | FPS |
|---|---:|---:|---:|
| S0 без передобробки | 0.289 | 177.6 | 5.63 |
| S2 тип → фільтр | 0.277 | 196.3 | 5.09 |
| S3 макс. точність | 0.570 | 189.2 | 5.28 |
| S4 поріг упевненості | 0.574 | 359.5 | 2.78 |
| **S5 запропонований** | **0.578** | **184.7** | **5.41** |

### Новизна: S5 vs S4 при рівній точності (`ci_s4`)

| Метрика | Значення |
|---|---|
| mAP (обидві) | 0.578 |
| перевага FPS S5 | **86.7 %** |
| 95% ДІ (фіксований τ) | [80.4; 92.3] % |
| 95% ДІ (τ у кожній бутстреп-вибірці) | [71.5; 94.0] %, медіана 84.2 % |

Порівняння з попереднім new-стендом до правок: було **53.6 %** → стало **86.7 %**.

### Перевірка \(d_b(L)\), \(d_n(\sigma)\) на train (400 кадрів)

| L | сер. \(d_b\) | σ | сер. \(d_n\) |
|---:|---:|---:|---:|
| 0 | 0.156 | 0 | 0.092 |
| 5 | 0.350 | 5 | 0.405 |
| 9 | 0.568 | 10 | 0.890 |
| 15 | 0.699 | 20 | 1.000 |

\(\rho(d_b,L)\approx 0.694\), \(\rho(d_n,\sigma)\approx 0.973\).

### Unit-тести C

```bash
mingw32-make test
# ALL PASS (0 failures)
```

Перевіряється: відносна маска, \(d_n=0\) без плоских точок, монотонність \(d_b\) і \(n_{\mathrm{flat}}\), усі маршрути, селектор, pipeline.

---

## 15. Відповідність зауваженням

| Вимога | Реалізація |
|---|---|
| Вектор \((d_u,d_o,d_c,d_n,d_b)\) | `AdAssess.v[5]` |
| Тип лише для журналу | `log_kind` / `log_state` |
| Прибрати «OK → не обробляти» | рішення тільки в `ad_select_route` |
| Підібрати \(s_{L0}\), ріст \(d_b\) з L | block sharpness + \(s_{L0}=0.3345\) |
| Відносна плоска маска | `flat_frac`, `ad_flat_residual` |
| Свої маршрути + вартість | `routes.c` + стенд `OWN_ROUTES` |
| Селектор замість decide | `select.c` + `selector_tree.c` / S5 |
| Перерахунок експерименту | `sim_stand_new_fix`, 86.7 % |

---

## 16. Обмеження

- Абсолютні FPS залежать від машини; порівнювати слід відносні показники на одному прогоні.
- Дерево в C навчене на синтетичному сурогаті; для публікації чисел роботи використовуйте S5 зі стенду (еталони за AP детектора).
- \(d_n\) майже насичується при \(\sigma=20\); зсув 1.35 — емпіричний.
- Результати — синтетичний стенд + модельний HOG+SVM, не реальний відеопотік БПЛА.
