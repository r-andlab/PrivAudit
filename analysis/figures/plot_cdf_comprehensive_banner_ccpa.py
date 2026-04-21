#!/usr/bin/env python3
"""CDF of websites by cookie count across consent stages, using comprehensive dataset for banner websites, split by CCPA."""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import os

SPINE_COLOR = 'gray'

def latexify(fig_width=None, fig_height=None, columns=2):

    assert columns in [1, 2]
    if fig_width is None:
        fig_width = 3.39 if columns == 1 else 6.9  # inches

    if fig_height is None:
        golden_mean = (np.sqrt(5) - 1.0) / 2.0  # aesthetic ratio
        fig_height = fig_width * golden_mean

    MAX_HEIGHT_INCHES = 8.0
    if fig_height > MAX_HEIGHT_INCHES:
        fig_height = MAX_HEIGHT_INCHES

    params = {
        'axes.labelsize'  : 12,
        'axes.titlesize'  : 12,
        'font.size'       : 12,
        'legend.fontsize' : 11,
        'xtick.labelsize' : 11,
        'ytick.labelsize' : 11,
        'figure.figsize'  : [fig_width, fig_height],
        'font.family'     : 'serif',
        'font.serif'      : ['Times New Roman', 'Times', 'DejaVu Serif', 'serif'],
        'text.usetex'     : False,
    }
    matplotlib.rcParams.update(params)
    return params

def format_axes(ax):
    """Make axes look cleaner and consistent with the template."""
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_color(SPINE_COLOR)
        ax.spines[spine].set_linewidth(0.5)

    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')

    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_tick_params(direction='in', color=SPINE_COLOR)

    ax.grid(color='black', linestyle='-.', linewidth=0.5, alpha=0.7, which='both', axis='both')
    ax.set_facecolor('w')
    return ax

# =========================
# Configuration
# =========================
COMPREHENSIVE_PATH = "../Analysis/final_default_state_comprehensive_reclassified.csv"
BANNER_PATH = "../Analysis/cookie_data_final - Banner_present.csv"
OUTDIR = "paper/figures/new_figures"
os.makedirs(OUTDIR, exist_ok=True)

WEBSITE_COL = "website"
CCPA_COL = "CCPA_Category"
STAGES = {
    "Initial": "initial_cookies",
    "Accept":  "consent_accept",
    "Reject":  "consent_reject",
}
MAX_X = None

# =========================
# Helpers
# =========================
def normalize_ccpa(val: str) -> str:
    """Normalize CCPA values to Subject/Not-Subject."""
    if not isinstance(val, str):
        return "Not-Subject"
    v = val.strip()
    if v == "Subject to CCPA":
        return "Subject"
    else:
        return "Not-Subject"

def present_mask(series: pd.Series) -> pd.Series:
    """Check if cookie is present in this stage (non-empty value)."""
    s = series.astype(str).str.strip().str.lower()
    return ~s.isin(["", "nan", "none"])

def per_site_counts(df: pd.DataFrame, stage_col: str) -> pd.Series:
    """Count cookies per site for a given stage."""
    d = df.loc[present_mask(df[stage_col]), [WEBSITE_COL, stage_col]].copy()
    return d.groupby(WEBSITE_COL).size().astype(int)

def build_cdf_abs(counts: pd.Series, k_max: int):
    """Build absolute CDF: (k, count of sites with ≤k cookies)."""
    x = np.arange(0, k_max + 1, dtype=int)
    y = np.fromiter(((counts <= k).sum() for k in x), dtype=int, count=len(x))
    return x, y

# =========================
# Load & prepare
# =========================
print(f"Loading banner dataset from: {BANNER_PATH}")
df = pd.read_csv(BANNER_PATH, dtype=str)
print(f"Loaded {len(df):,} cookies from {df[WEBSITE_COL].nunique()} websites with consent banners")

print(f"\nLoading comprehensive dataset for CCPA info from: {COMPREHENSIVE_PATH}")
comp_df = pd.read_csv(COMPREHENSIVE_PATH, dtype=str)

# Get CCPA_Category mapping from comprehensive
site_ccpa_map = (
    comp_df.groupby([WEBSITE_COL, CCPA_COL]).size()
           .reset_index(name="n")
           .sort_values([WEBSITE_COL, "n"], ascending=[True, False])
           .drop_duplicates(subset=[WEBSITE_COL], keep="first")[[WEBSITE_COL, CCPA_COL]]
)

# Merge CCPA_Category into banner data (inner join - only keep websites with CCPA info)
df = df.merge(site_ccpa_map, on=WEBSITE_COL, how="inner")
print(f"After merge: {len(df):,} cookies from {df[WEBSITE_COL].nunique()} websites with CCPA info")

df = df[~df[WEBSITE_COL].isna()].copy()
df[WEBSITE_COL] = df[WEBSITE_COL].astype(str)

# Normalize CCPA column
df["CCPA_Group"] = df[CCPA_COL].apply(normalize_ccpa)

# Get CCPA assignment per website (take most common label per site)
site_ccpa = (
    df.groupby([WEBSITE_COL, "CCPA_Group"]).size()
      .reset_index(name="n")
      .sort_values([WEBSITE_COL, "n"], ascending=[True, False])
      .drop_duplicates(subset=[WEBSITE_COL], keep="first")[[WEBSITE_COL, "CCPA_Group"]]
      .set_index(WEBSITE_COL)["CCPA_Group"]
)

print(f"\nCCPA breakdown:")
print(site_ccpa.value_counts())

# Process each CCPA group separately
results = {}

for ccpa_group in ["Subject", "Not-Subject"]:
    sites_in_group = site_ccpa[site_ccpa == ccpa_group].index.tolist()
    df_group = df[df[WEBSITE_COL].isin(sites_in_group)].copy()

    # Count cookies per site for each stage
    counts_by_stage = {name: per_site_counts(df_group, col) for name, col in STAGES.items()}

    # Reindex to include all sites in this group
    for k in counts_by_stage:
        counts_by_stage[k] = counts_by_stage[k].reindex(sites_in_group, fill_value=0)

    results[ccpa_group] = {
        "sites": sites_in_group,
        "counts": counts_by_stage,
        "n_sites": len(sites_in_group)
    }

# Determine x-axis range (use global max)
all_counts = []
for ccpa_group in results:
    for stage in results[ccpa_group]["counts"].values():
        all_counts.extend(stage.values)

max_seen = int(max(all_counts)) if all_counts else 0
if MAX_X is None:
    p99 = int(np.percentile(all_counts, 99)) if all_counts else 0
    MAX_X = max(10, min(max_seen, p99 + 5))

print(f"\nX-axis range: 0 to {MAX_X}")

# Build CDF curves for each group
for ccpa_group in results:
    results[ccpa_group]["cdfs"] = {
        name: build_cdf_abs(results[ccpa_group]["counts"][name], MAX_X)
        for name in STAGES.keys()
    }

# Print statistics
print("\nStatistics per stage and CCPA group:")
for ccpa_group in ["Subject", "Not-Subject"]:
    print(f"\n{ccpa_group} (N={results[ccpa_group]['n_sites']}):")
    for name in ["Initial", "Accept", "Reject"]:
        s = results[ccpa_group]["counts"][name]
        print(f"  {name:>7}: median={int(np.median(s))}, P90={int(np.percentile(s,90))}, "
              f"P95={int(np.percentile(s,95))}, max={int(s.max())}")

# =========================
# Plot
# =========================
latexify(columns=2)

fig, ax = plt.subplots(figsize=(7, 4))

# Colors for each stage × CCPA group combination (different colors for solid vs dashed)
colors_map = {
    ("Initial", "Subject"): "black",
    ("Initial", "Not-Subject"): "dimgray",
    ("Accept", "Subject"): "tab:blue",
    ("Accept", "Not-Subject"): "tab:cyan",
    ("Reject", "Subject"): "tab:red",
    ("Reject", "Not-Subject"): "tab:orange",
}
# Line styles for CCPA groups
ccpa_styles = {"Subject": "-", "Not-Subject": "--"}
# Markers
stage_markers = {"Initial": "o", "Accept": "s", "Reject": "v"}

for ccpa_group in ["Subject", "Not-Subject"]:
    for stage in ["Initial", "Accept", "Reject"]:
        x, y = results[ccpa_group]["cdfs"][stage]

        label = f"{stage} ({ccpa_group})"

        ax.step(x, y, where="post", linewidth=2.5, alpha=1.0,
                color=colors_map[(stage, ccpa_group)], linestyle=ccpa_styles[ccpa_group],
                label=label)

        # Add markers at intervals
        mk_idx = (x % 5 == 0)
        ax.plot(x[mk_idx], y[mk_idx], linestyle="None",
                marker=stage_markers[stage], ms=6.5,
                color=colors_map[(stage, ccpa_group)], alpha=1.0)

# Get max y (total unique sites)
max_y = len(site_ccpa)

ax.set_xlim(0, MAX_X)
ax.set_ylim(0, max_y)

ax.set_xlabel(r"Cookies per site ($\leq k$)", fontsize=22)
ax.set_ylabel("Websites with $\leq k$ cookies", fontsize=22)

# Legend with 2 columns to fit all 6 lines
leg = ax.legend(frameon=True, ncol=2,
                loc="lower center", bbox_to_anchor=(0.5, 1.02),
                fontsize=14)

for tick in ax.get_yticklabels():
    tick.set_fontsize(22)
for tick in ax.get_xticklabels():
    tick.set_fontsize(22)

format_axes(ax)

fig.subplots_adjust(top=0.80, bottom=0.15, left=0.12, right=0.96)

# Save
png_path = os.path.join(OUTDIR, "cdf_comprehensive_banner_ccpa_split.png")
pdf_path = os.path.join(OUTDIR, "cdf_comprehensive_banner_ccpa_split.pdf")
fig.savefig(png_path, dpi=300, bbox_inches="tight")
fig.savefig(pdf_path, bbox_inches="tight")

print(f"\nSaved: {pdf_path}")
print(f"Saved: {png_path}")
