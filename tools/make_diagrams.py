"""Draw the workflow and algorithm flowcharts used in the documents.

    python tools/make_diagrams.py   ->  docs/figures/fig_workflow.png, fig_algorithm.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
FILL = {"data": "#cde2fb", "proc": "#f0efec", "core": "#86b6ef", "out": "#f9c4a8", "dec": "#fde3d5"}


def box(ax, x, y, w, h, text, kind="proc", fs=8.5):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=FILL[kind], ec=INK2, lw=0.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK, wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10, color=INK2, lw=0.9))
    if text:
        ax.text((x1 + x2) / 2 + 0.05, (y1 + y2) / 2, text, fontsize=7, color=INK2, va="center")


def workflow():
    fig, ax = plt.subplots(figsize=(11, 7.2))
    fig.patch.set_facecolor(SURF)
    ax.set_xlim(0, 11); ax.set_ylim(-0.4, 7.4); ax.axis("off")
    box(ax, 1.6, 6.7, 2.6, 0.7, "FMS records (*.csv)\nnew files -> data/inbox", "data")
    box(ax, 1.6, 5.7, 2.6, 0.7, "Survey change solids (*.dxf)\nnew files -> data/inbox", "data")
    box(ax, 1.6, 4.6, 2.6, 0.8, "config/project.yaml\nsurvey_overrides.csv\n(assumptions A-xx)", "dec")
    box(ax, 4.7, 6.2, 2.6, 0.9, "1-2 IMPORT\nscan sources, SHA-256 registry,\nstandardise, rasterise (cache)", "proc")
    box(ax, 4.7, 4.9, 2.6, 0.9, "3 QA/QC\n14 FMS flags, survey checks,\ncoverage, alignment", "proc")
    box(ax, 4.7, 3.6, 2.6, 0.9, "4 PERIODS\nsurvey times, gap detection,\nloads -> periods", "proc")
    box(ax, 4.7, 2.2, 2.6, 1.1, "5 MATERIAL MOVEMENT (CPST)\ncuts, push cost, partial OT,\ndeposit layers, carry-over", "core")
    box(ax, 8.0, 6.2, 2.7, 0.9, "6-7 BLOCK MODEL\n5x5x2 m, tonnes, Cu, Au, Ag,\nmetal, class, provenance", "core")
    box(ax, 8.0, 4.9, 2.7, 0.9, "8 UNCERTAINTY\nMonte Carlo (60) + tornado;\nP10/P50/P90, CV, confidence", "proc")
    box(ax, 8.0, 3.6, 2.7, 0.9, "9 VALIDATION\nmass/metal balance, geometry,\nforward test, twin, robustness", "proc")
    box(ax, 8.0, 2.2, 2.7, 1.0, "10 OUTPUTS\nCSV / VTK / ASC exports,\nfigures, report tables", "out")
    box(ax, 8.0, 0.8, 2.7, 0.9, "11 AUDIT\nrun manifest, config hash, versions,\nhistory + change report", "out")
    arrow(ax, 2.9, 6.7, 3.4, 6.35); arrow(ax, 2.9, 5.7, 3.4, 6.05)
    arrow(ax, 2.9, 4.6, 3.4, 3.7); arrow(ax, 2.9, 4.5, 3.4, 2.4)
    arrow(ax, 4.7, 5.75, 4.7, 5.35); arrow(ax, 4.7, 4.45, 4.7, 4.05); arrow(ax, 4.7, 3.15, 4.7, 2.75)
    arrow(ax, 6.0, 2.4, 6.65, 5.9)
    arrow(ax, 8.0, 5.75, 8.0, 5.35); arrow(ax, 8.0, 4.45, 8.0, 4.05); arrow(ax, 8.0, 3.15, 8.0, 2.7); arrow(ax, 8.0, 1.7, 8.0, 1.25)
    ax.text(0.2, -0.25, "python -m spbm update  : picks up new files, re-runs steps 1-11, writes a change report against the previous model version",
            fontsize=8, color=INK2)
    ax.set_title("SPBM platform workflow (steps numbered as in the course outline, Task 8)", loc="left", fontsize=11, fontweight="bold")
    fig.savefig(OUT / "fig_workflow.png", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def algorithm():
    fig, ax = plt.subplots(figsize=(9.5, 10.5))
    fig.patch.set_facecolor(SURF)
    ax.set_xlim(0, 10); ax.set_ylim(0, 11.2); ax.axis("off")
    x = 5
    steps = [
        (10.5, "State at survey s-1: column stacks (legacy + earlier period layers), model surface z_m,\ncarried platform parcels", "data"),
        (9.4, "Read change solid s: top_s, bot_s.  First-surveyed cells -> create legacy column to prior surface\n(bot_s, or repose extrapolation if in front of an earlier face: A-13b)", "proc"),
        (8.3, "Cut detection: bot_s < z_m - tau on previously surveyed cells -> remove top of column\n-> cut sources (re-handled material, A-20)", "proc"),
        (7.2, "Fill field: dZ = top_s - z_m > tau  ->  sink capacity  b_c = dZ_c * A  (m3)", "proc"),
        (6.1, "Sources: loads of period s (v_k = m_k / rho_k), carried parcels, cut cells\n+ dummy source U (unattributed); sinks: fill cells + dummy sink R (retained)", "proc"),
        (5.0, "Push cost C_kc = slope-aware geodesic distance on pre-period surface\n(w = l + alpha * uphill rise; C = inf beyond L_max); C_kR = c_R, C_Uc = c_U, C_UR = 0", "core"),
        (3.9, "Entropic optimal transport (log-domain Sinkhorn, mixing length eps):\nmin <P,C> - eps H(P) s.t. P1 = a, P^T 1 = b ; rows rescaled -> exact mass", "core"),
        (2.8, "Deposit: layer_c = sum_k P_kc * pi_k  (volume, tonnes, Cu, Au, Ag, age),\nlayer top = surveyed top_s  (gravity / repose honoured by the survey)", "core"),
        (1.7, "R column -> parcels carried to period s+1 (dozer lag); U -> 'unattributed' class with imputed grade", "proc"),
        (0.6, "z_m <- column tops; s <- s+1.  After last survey: retained parcels spread on unsurveyed platform;\npost-survey loads -> forward model nowcast (provisional)", "out"),
    ]
    for y, t, k in steps:
        box(ax, x, y, 9.2, 0.85, t, k, fs=8.2)
    for (y1, _, _), (y2, _, _) in zip(steps[:-1], steps[1:]):
        arrow(ax, x, y1 - 0.43, x, y2 + 0.43)
    ax.set_title("CPST - Constrained Push-and-Settle Transport: one survey period", loc="left", fontsize=11, fontweight="bold")
    fig.savefig(OUT / "fig_algorithm.png", dpi=170, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    workflow()
    algorithm()
    print("written", OUT)
