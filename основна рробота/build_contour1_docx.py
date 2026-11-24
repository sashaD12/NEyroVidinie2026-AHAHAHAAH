# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT_DIR = Path(__file__).resolve().parent
FORMULA_DIR = OUT_DIR / "_formula_png"
OUT_DOCX = OUT_DIR / "Контур_1_повний_опис.docx"


def set_run_font(run, name: str = "Times New Roman", size: int = 12, bold: bool = False) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        set_run_font(run, size=16 if level == 1 else 14, bold=True)


def add_para(doc: Document, text: str, size: int = 12, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    p.paragraph_format.space_after = Pt(6)


def render_formula(latex: str, name: str, fontsize: int = 18) -> Path:
    FORMULA_DIR.mkdir(parents=True, exist_ok=True)
    path = FORMULA_DIR / f"{name}.png"
    fig = plt.figure(figsize=(9, 1.6))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(
        0.5,
        0.5,
        f"${latex}$",
        fontsize=fontsize,
        ha="center",
        va="center",
        color="black",
    )
    fig.savefig(path, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    return path


def add_formula(doc: Document, latex: str, name: str, fontsize: int = 18, width_cm: float = 14.0) -> None:
    path = render_formula(latex, name, fontsize=fontsize)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, bold=True, size=11)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(val)
            set_run_font(run, size=10)
    doc.add_paragraph()


def build() -> Path:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Контур 1. Повний опис методу аналізу кадру")
    set_run_font(run, size=18, bold=True)

    add_para(
        doc,
        "Контур 1 аналізує grayscale-кадр на subsample-сітці 160×120 і визначає тип пошкодження (kind), "
        "силу пошкодження та стан кадру (OK / REPAIR / BAD).",
    )
    add_para(
        doc,
        "На одній сітці працюють два шари: (A) світло — гістограма яскравості; "
        "(B) простір — Laplacian (розмиття) і residual у flat-зонах (шум). "
        "Пріоритет: спочатку світло; якщо світло в нормі, тоді шум/розмиття.",
    )

    add_heading(doc, "0. Subsample (сітка оцінки)", 1)
    add_para(doc, "Кадр розміру W×H зводиться до сітки 160×120:")
    add_formula(doc, r"\Delta x=\max\left(1,\frac{W}{160}\right),\quad \Delta y=\max\left(1,\frac{H}{120}\right)", "s0_delta", 16)
    add_formula(doc, r"I_g(s_x,s_y)=I\!\left(\lfloor s_x\cdot\Delta x\rfloor,\ \lfloor s_y\cdot\Delta y\rfloor\right)", "s0_sample", 14)
    add_para(doc, "де s_x ∈ [0..159], s_y ∈ [0..119]. Гістограма і Laplacian — на цій сітці; residual шуму бере full-res сусідів тих самих точок.")

    add_heading(doc, "Шар A. Світлові пошкодження", 1)

    add_heading(doc, "A1. Гістограма, середнє μ, розкид σ", 2)
    add_para(doc, "h[i] — кількість точок із яскравістю i ∈ [0..255]. N — кількість точок сітки.")
    add_formula(doc, r"\mu=\frac{1}{N}\sum_{i=0}^{255} i\cdot h[i]", "a1_mu", 16)
    add_formula(doc, r"\sigma=\sqrt{\frac{1}{N}\sum_{i=0}^{255} i^{2} h[i]-\mu^{2}}", "a1_sigma", 16)
    add_para(doc, "μ — середня яскравість кадру. σ — «ширина» гістограми (глобальний контраст, не шум).")
    add_para(doc, "Дефолти: μ₀ = 80, μ₁ = 180, σ₀ = 40.")

    add_heading(doc, "A2. Хвости гістограми", 2)
    add_para(doc, "Частка майже чорних і майже білих пікселів:")
    add_formula(doc, r"p_b=\frac{1}{N}\sum_{i=0}^{10} h[i],\qquad p_s=\frac{1}{N}\sum_{i=245}^{255} h[i]", "a2_pb_ps", 13, 15)
    add_para(doc, "Широкий темний блок:")
    add_formula(doc, r"p_{dark}=\frac{1}{N}\sum_{i=0}^{55} h[i]", "a2_pdark", 16)
    add_para(doc, "Нормалізатор хвостів: p_max = 0.5.")

    add_heading(doc, "A3. Damage світла", 2)
    add_para(doc, "Недоекспозиція d_u — максимум із трьох ознак «занадто темно»:")
    add_formula(
        doc,
        r"d_u=\mathrm{clamp}_{[0,1]}\left(\max\left(\frac{\mu_0-\mu}{\mu_0},\ \frac{p_b}{p_{max}},\ \frac{p_{dark}}{0.75}\right)\right)",
        "a3_du",
        12,
        15.5,
    )
    add_para(doc, "Переекспозиція d_o:")
    add_formula(
        doc,
        r"d_o=\mathrm{clamp}_{[0,1]}\left(\max\left(\frac{\mu-\mu_1}{255-\mu_1},\ \frac{p_s}{p_{max}}\right)\right)",
        "a3_do",
        13,
        15,
    )
    add_para(doc, "Низький контраст d_c:")
    add_formula(doc, r"d_c=\mathrm{clamp}_{[0,1]}\left(1-\frac{\sigma}{\sigma_0}\right)", "a3_dc", 16)
    add_para(doc, "Якщо σ ≥ 40 → d_c = 0 (контрасту досить). Якщо σ → 0 → d_c → 1 («сірий» кадр).")
    add_para(doc, "Агрегат світла:")
    add_formula(doc, r"d_l=\max(d_u,\ d_o,\ d_c)", "a3_dl", 16)

    add_heading(doc, "A4. Класифікація світлового kind", 2)
    add_para(doc, "Пороги: τ_l = 0.35, t_l = 0.85.")
    add_table(
        doc,
        ["Умова", "kind", "уточнення d_l"],
        [
            ["d_u≥τ_l і d_o≥τ_l, або p_s≥0.12 і p_dark≥0.12", "MIXED", "max(d_u,d_o); якщо <τ_l → τ_l+0.05"],
            ["d_u≥τ_l і домінує d_u", "UNDER", "max(d_u, d_c)"],
            ["d_o≥τ_l і домінує d_o", "OVER", "max(d_o, d_c)"],
            ["d_c≥τ_l", "CONTRAST", "d_c"],
        ],
    )

    add_heading(doc, "A5. Severity світла r_L", 2)
    add_para(doc, "Кусочно-лінійна шкала:")
    add_para(doc, "якщо d_l ≤ τ_l:", bold=True)
    add_formula(doc, r"r_L=0", "a5_rl0", 16, 6)
    add_para(doc, "якщо τ_l < d_l < t_l:", bold=True)
    add_formula(doc, r"r_L=\frac{d_l-\tau_l}{t_l-\tau_l}", "a5_rl1", 16, 10)
    add_para(doc, "якщо d_l ≥ t_l:", bold=True)
    add_formula(doc, r"r_L=1", "a5_rl2", 16, 6)
    add_para(doc, "Якщо r_L > 0, кадр уже вважається світлово пошкодженим: просторовий шар не змінює kind.")

    add_heading(doc, "Шар B. Шум і розмиття", 1)
    add_para(doc, "Рахується завжди, але керує kind лише якщо світло OK (r_L = 0).")

    add_heading(doc, "B1. Laplacian (локальна гострота)", 2)
    add_formula(
        doc,
        r"L(x,y)=I(x+1,y)+I(x-1,y)+I(x,y+1)+I(x,y-1)-4\,I(x,y)",
        "b1_lap",
        14,
        15.5,
    )
    add_para(doc, "Різкий край → |L| великий. Розмиття → L ≈ 0.")

    add_heading(doc, "B2. Метрика blur: дисперсія Лапласіана s_L", 2)
    add_formula(doc, r"\bar{L}=\frac{1}{M}\sum L(x,y)", "b2_mean", 16)
    add_formula(doc, r"s_L=\mathrm{Var}(L)=\frac{1}{M}\sum L(x,y)^{2}-\bar{L}^{2}", "b2_var", 15)
    add_para(doc, "M — кількість точок, де рахували L. Чим менша s_L, тим сильніше розмиття.")

    add_heading(doc, "B3. Damage розмиття d_b", 2)
    add_formula(doc, r"d_b=\mathrm{clamp}_{[0,1]}\left(1-\frac{s_L}{s_{L0}}\right),\quad s_{L0}=100", "b3_db", 15)
    add_para(doc, "s_L ≥ 100 → d_b = 0. s_L → 0 → d_b → 1.")

    add_heading(doc, "B4. Residual після згладжування", 2)
    add_para(doc, "У точці subsample на full-res сусідах:")
    add_formula(
        doc,
        r"\tilde{I}(x,y)=\frac{1}{9}\sum_{i=-1}^{1}\sum_{j=-1}^{1} I(x+i,\ y+j)",
        "b4_mean",
        14,
        14,
    )
    add_formula(doc, r"R(x,y)=\left|I(x,y)-\tilde{I}(x,y)\right|", "b4_r", 16)
    add_para(doc, "R показує, наскільки піксель «стрибає» відносно локального середнього 3×3.")

    add_heading(doc, "B5. Градієнт (сила краю)", 2)
    add_formula(
        doc,
        r"|\nabla I|\approx |I(x+1,y)-I(x-1,y)|+|I(x,y+1)-I(x,y-1)|",
        "b5_grad",
        14,
        15.5,
    )

    add_heading(doc, "B6. Flat-mask", 2)
    add_para(doc, "Точка плоска, якщо:")
    add_formula(doc, r"|\nabla I|<\tau_e,\qquad \tau_e=24", "b6_flat", 16)
    add_para(doc, "Шум міряємо лише там, де немає сильного краю/текстури.")

    add_heading(doc, "B7. Метрика шуму n_flat", 2)
    add_formula(
        doc,
        r"n_{flat}=\mathrm{mean}(R\mid |\nabla I|<\tau_e)=\frac{1}{|F|}\sum_{(x,y)\in F}R(x,y)",
        "b7_nflat",
        12,
        15.5,
    )

    add_heading(doc, "B8. Damage шуму d_n", 2)
    add_formula(doc, r"d_n=\mathrm{clamp}_{[0,1]}\left(\frac{n_{flat}}{n_0}\right),\quad n_0=8", "b8_dn", 15)

    add_heading(doc, "B9. Spatial damage і severity", 2)
    add_formula(doc, r"d_s=\max(d_n,\ d_b)", "b9_ds", 16)
    add_para(doc, "Severity r(d, τ, t):")
    add_para(doc, "якщо d ≤ τ:", bold=True)
    add_formula(doc, r"r=0", "b9_r0", 16, 6)
    add_para(doc, "якщо τ < d < t:", bold=True)
    add_formula(doc, r"r=\frac{d-\tau}{t-\tau}", "b9_r1", 16, 10)
    add_para(doc, "якщо d ≥ t:", bold=True)
    add_formula(doc, r"r=1", "b9_r2", 16, 6)
    add_para(doc, "τ_n = τ_b = 0.35, t_n = t_b = 0.85. Окремо: r_n = r(d_n,…), r_b = r(d_b,…).")

    add_heading(doc, "Злиття шарів (fuse)", 1)
    add_para(doc, "1) Якщо r_L > 0 → kind = UNDER / OVER / CONTRAST / MIXED, r = r_L.")
    add_para(doc, "2) Інакше, якщо є просторове пошкодження → kind = NOISE або BLUR, r = r_n або r_b.")
    add_para(doc, "3) Інакше → kind = NONE, r = 0.")
    add_table(
        doc,
        ["r", "state"],
        [["r = 0", "OK"], ["0 < r < 1", "REPAIR"], ["r = 1", "BAD"]],
    )

    add_heading(doc, "Підсумок", 1)
    add_para(
        doc,
        "Контур 1 — швидкий повний assess кадру: гістограма вирішує світло; "
        "Laplacian / flat-residual — різкість і шум; без SURF; сітка 160×120. "
        "Код: c/contour_1 (ad_assess_frame у src/assess.c).",
    )

    # Word may lock the file if open; write temp then replace
    tmp = OUT_DOCX.with_suffix(".tmp.docx")
    doc.save(str(tmp))
    try:
        if OUT_DOCX.exists():
            OUT_DOCX.unlink()
        os.replace(tmp, OUT_DOCX)
    except PermissionError:
        alt = OUT_DIR / "Контур_1_повний_опис_ФОРМУЛИ.docx"
        os.replace(tmp, alt)
        return alt
    return OUT_DOCX


if __name__ == "__main__":
    out = build()
    print(out)
