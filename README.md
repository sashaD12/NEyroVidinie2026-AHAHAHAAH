# Contour 1 final (new_fix)

Фінальна C-версія Контуру 1 після зауважень (друга / «new» лінія).

## Збірка

```bash
mingw32-make all
mingw32-make test
```

## Запуск

```bash
bin/ad_enhance.exe input.jpg output.png
bin/bench_assess.exe --iters 200 path/to/frame.jpg
```

## Документація

Повний опис методів, формул і прикладів коду: [`docs/TECHNICAL.md`](docs/TECHNICAL.md).

Результати стенду: [`docs/results/`](docs/results/).

## Стенд

Копія фінального стенду: [`stand_new_fix/`](stand_new_fix/) (підхоплює `../bin/contour_1.dll`).

```bash
cd stand_new_fix
set PYTHONUTF8=1
python analyze.py 0.05
python ci_s4.py
```
