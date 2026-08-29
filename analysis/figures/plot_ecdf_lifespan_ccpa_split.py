# Usage: python plot_ecdf_lifespan_ccpa_split.py  |  ECDF of cookie lifespan by category, split by CCPA subjectivity (re-verified labels).
import numpy as np
import pandas as pd
import scipy
import matplotlib.pyplot as plt
import scipy.stats as ss
from matplotlib import mlab
import os, sys, math, shutil, re
from collections import defaultdict, OrderedDict
import seaborn as sns
import copy as copy
from matplotlib.patches import Arc
import matplotlib
from itertools import cycle, islice
import matplotlib.dates as mdates
from matplotlib import gridspec
from math import sqrt

SPINE_COLOR = 'gray'

def latexify(fig_width=None, fig_height=None, columns=1):
    assert(columns in [1,2])
    if fig_width is None:
        fig_width = 3.39 if columns==1 else 6.9
    if fig_height is None:
        golden_mean = (sqrt(5)-1.0)/2.0
        fig_height = fig_width*golden_mean
    MAX_HEIGHT_INCHES = 8.0
    if fig_height > MAX_HEIGHT_INCHES:
        fig_height = MAX_HEIGHT_INCHES
    params = {
        'backend': 'ps',
        'text.latex.preamble': ['\\usepackage{gensymb}'],
        'axes.labelsize': 8,
        'axes.titlesize': 8,
        'font.size': 8,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'text.usetex': True,
        'figure.figsize': [fig_width,fig_height],
        'font.family': 'times new roman'
    }
    return params

def apply_template_safe(params: dict):
    p = dict(params)
    if shutil.which("latex") is None:
        p['text.usetex'] = False
        p.pop('text.latex.preamble', None)
    matplotlib.rcParams.update(p)

def format_axes(ax):
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_color(SPINE_COLOR)
        ax.spines[spine].set_linewidth(0.5)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_tick_params(direction='in', color=SPINE_COLOR)
    return ax

if not matplotlib.rcParams.get('text.usetex', False):
    matplotlib.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    })

BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CSV_PATH = f"{BASE}/data/final_default_state_comprehensive_NEWLABELS.csv"
OUT_DIR = f"{BASE}/figures_output"
OUT_NAME = "ecdf_counts_cookie_types_default_subjected_vs_nonsubjected"
os.makedirs(OUT_DIR, exist_ok=True)

CANON_TYPES_MAP = {
    "targeting": "Targeting",
    "performance": "Performance",
    "functional": "Functional",
    "strictly necessary": "Strictly Necessary",
    "necessary": "Strictly Necessary",
    "unknown": "Unknown",
}

TYPE_ORDER = [
    "Targeting",
    "Performance",
    "Functional",
    "Strictly Necessary",
    "Unknown",
]

def norm_category(val: str) -> str:
    if not isinstance(val, str):
        return "Unknown"
    key = val.strip().lower()
    return CANON_TYPES_MAP.get(key, "Unknown")

def norm_ccpa(val: str) -> str:
    v = str(val).strip()
    return "Subjected" if v == "Subject to CCPA" else "Non-Subj."

def to_days(x):
    try:
        v = float(x)
        return v / 86400.0
    except Exception:
        return np.nan

def ecdf(yvals):
    x = np.sort(np.asarray(yvals))
    n = len(x)
    if n == 0:
        return np.array([]), np.array([])
    y = np.arange(1, n+1) / n
    return x, y

print(f"Loading dataset from: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, dtype=str)
print(f"Loaded {len(df):,} cookies")

needed = {"CCPA_Category", "category", "remaining_expiry_time", "session"}
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns in CSV: {missing}")

df["Cookie Type"] = df["category"].apply(norm_category)
df["Group"] = df["CCPA_Category"].apply(norm_ccpa)

df["lifespan_days"] = df["remaining_expiry_time"].apply(to_days)

mask_type = df["Cookie Type"].isin(TYPE_ORDER)
mask_session = df["session"].astype(str).str.upper().eq("TRUE")
mask_pos = df["lifespan_days"].notna() & (df["lifespan_days"] > 0)

df_f = df[mask_type & ~mask_session & mask_pos].copy()

print(f"\nAfter filtering:")
print(f"  Total cookies: {len(df_f):,}")
print(f"  Cookie types: {sorted(df_f['Cookie Type'].unique())}")
print(f"  CCPA groups: {sorted(df_f['Group'].unique())}")
print(f"  Lifespan range: {df_f['lifespan_days'].min():.2f} - {df_f['lifespan_days'].max():.2f} days")

fig, ax = plt.subplots(figsize=(6, 4))

color_cycle = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown", "tab:pink"]
type_colors = list(islice(cycle(color_cycle), None, len(TYPE_ORDER)))
marker_cycle = ["o", "s", "^", "D", "P", "X", "v"]
type_markers = list(islice(cycle(marker_cycle), None, len(TYPE_ORDER)))
ls_for_group = {'Subjected': '-', 'Non-Subj.': '--'}

present_types = [t for t in TYPE_ORDER if t in set(df_f["Cookie Type"].unique())]

for i, ctype in enumerate(present_types):
    for grp in ['Subjected', 'Non-Subj.']:
        vals = df_f.loc[(df_f["Cookie Type"] == ctype) & (df_f["Group"] == grp), "lifespan_days"].values
        if len(vals) == 0:
            continue
        x, y = ecdf(vals)

        label = f"{ctype} ({grp})"

        ax.plot(
            x, y,
            lw=1.2,
            color=type_colors[i],
            linestyle=ls_for_group[grp],
            marker=type_markers[i],
            markevery=max(1, len(x) // 20),
            ms=3,
            alpha=0.9,
            label=label
        )

ax.set_xlim(0, 400)
ax.set_ylim(0, 1)
ax.set_xlabel("Cookie lifespan (days)", fontsize=20)
ax.set_ylabel("Fraction of cookies", fontsize=20)

for tick in ax.get_yticklabels():
    tick.set_fontsize(20)
for tick in ax.get_xticklabels():
    tick.set_fontsize(20)

ax.set_facecolor('w')
ax.grid(color='black', linestyle='-.', linewidth=0.3, alpha=0.5, which='both')
ax.xaxis.grid(True)
ax.tick_params(axis='y', which='major', direction='in', length=4, width=1.0, color='black', bottom=True, left=True)
ax.tick_params(axis='x', which='major', direction='in', length=4, width=1.0, color='black', bottom=True, left=True)

handles, labels = ax.get_legend_handles_labels()

def sort_key(lbl):
    for idx, t in enumerate(TYPE_ORDER):
        if lbl.startswith(t):
            return (idx, 0 if "(Subjected)" in lbl else 1)
    return (99, 0)

order = sorted(range(len(labels)), key=lambda i: sort_key(labels[i]))
handles = [handles[i] for i in order]
labels = [labels[i] for i in order]

label_map = {
    "(Subjected)": "(CCPA-Subject)",
    "(Non-Subj.)": "(CCPA-Not-Subject)"
}

new_labels = []
for lbl in labels:
    for old, new in label_map.items():
        lbl = lbl.replace(old, new)
    new_labels.append(lbl)

leg = ax.legend(handles, new_labels, loc='lower center', ncol=2, fontsize=12, frameon=True, bbox_to_anchor=(0.45, 1.18))

format_axes(ax)
fig.tight_layout()

pdf_path = os.path.join(OUT_DIR, OUT_NAME + ".pdf")
png_path = os.path.join(OUT_DIR, OUT_NAME + ".png")
fig.savefig(pdf_path, bbox_inches="tight")
fig.savefig(png_path, dpi=300, bbox_inches="tight")
print(f"\nSaved: {pdf_path}")
print(f"Saved: {png_path}")
