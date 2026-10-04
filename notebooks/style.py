"""Shared chart style: one blue for the subject, gray for context, recessive axes."""
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

BLUE, GRAY, INK, MUTED = "#2a78d6", "#b8b7b0", "#0b0b0b", "#52514e"
plt.rcParams.update({
    "font.size": 11, "axes.edgecolor": GRAY, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": INK, "axes.spines.top": False,
    "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "x", "grid.color": "#e6e5e0",
    "axes.axisbelow": True, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
})


def save(fig, name, source):
    fig.tight_layout()
    fig.text(0.01, 0, source, fontsize=7.5, color=MUTED, va="top")
    fig.savefig(FIG / name, dpi=160, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("wrote", FIG / name)
