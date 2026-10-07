"""Shared figure style (static PNG figures for reports).

Colour rules: categorical hues in a fixed order; sequential = one hue light->dark;
diverging = blue <-> red with a neutral grey midpoint; thin marks; recessive grid.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402

CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
        "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
ORANGE = ["#fde3d5", "#f9c4a8", "#f5a47b", "#f0844f", "#eb6834", "#c9532a", "#a54220", "#7f3218"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8985"
GRID = "#e4e3df"
NEUTRAL = "#f0efec"

SEQ = LinearSegmentedColormap.from_list("seq_blue", BLUE)
SEQ_OR = LinearSegmentedColormap.from_list("seq_orange", ORANGE)
DIV = LinearSegmentedColormap.from_list("div", ["#104281", "#3987e5", "#9ec5f4", NEUTRAL, "#f5a3a2", "#e34948", "#9c2423"])
ELEV = LinearSegmentedColormap.from_list("elev", ["#f4f3ef", "#d6d4cc", "#a9a69b", "#77746a", "#4a483f"])
CONF_COLORS = {"High": "#184f95", "Medium": "#3987e5", "Low": "#9ec5f4", "Uninformed": "#d6d4cc"}
INFO_COLORS = {"FMS-reconciled": CAT[0], "Unattributed-imputed": CAT[1], "Legacy-assumed": "#bdbbb3", "Provisional": CAT[6]}


def setup():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.labelsize": 9,
        "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 8, "font.size": 9,
        "lines.linewidth": 2.0, "axes.prop_cycle": matplotlib.cycler(color=CAT),
        "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight",
    })


setup()


def plan_axes(ax, g, title=None, ticks=True):
    ax.set_aspect("equal")
    ax.set_xlim(g.extent[0], g.extent[1])
    ax.set_ylim(g.extent[2], g.extent[3])
    ax.grid(False)
    if ticks:
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.tick_params(axis="x", labelrotation=30)
    if title:
        ax.set_title(title, loc="left")


def raster(ax, z, g, cmap=SEQ, vmin=None, vmax=None, **kw):
    return ax.imshow(z, origin="lower", extent=g.extent, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", **kw)


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def note(fig, text):
    fig.text(0.01, -0.01, text, ha="left", va="top", fontsize=7.5, color=INK2, wrap=True)


def period_colors(n):
    idx = np.linspace(3, len(BLUE) - 1, max(n, 1)).round().astype(int)
    return [BLUE[i] for i in idx]


def discrete_cmap(colors):
    return ListedColormap(colors)
