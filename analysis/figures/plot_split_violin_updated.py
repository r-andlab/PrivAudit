#!/usr/bin/env python3
# ===== High-Quality Split-Violin Figure: Subjected vs Non-Subj. =====
# Updated with: larger figures, minimal whitespace, horizontal legend, larger fonts

import os, re
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
from urllib.parse import urlparse

# ---------- OUTPUT ----------
OUTDIR = "paper/figures/new_figures"
os.makedirs(OUTDIR, exist_ok=True)

# ---------- CONFIGS ----------
RAW_CONFIGS = [
    ("initial_cookies", "Default"),
    ("do_not_track", "DNT"),
    ("block_3rd_party", "Block 3rd-party"),
    ("ublock", "uBlock"),
    ("gpc_enabled", "GPC"),
]

# Map raw categories in the CSV to canonical cookie types used in figures
CANON_TYPES_MAP = {
    # Targeting
    "targeting": "Targeting Cookies",
    "targeting cookies": "Targeting Cookies",
    "advertising": "Targeting Cookies",
    # Performance
    "performance": "Performance Cookies",
    "performance cookies": "Performance Cookies",
    "analytics": "Performance Cookies",
    # Functional
    "functional": "Functional Cookies",
    "functional cookies": "Functional Cookies",
    # Necessary / strictly necessary
    "strictly necessary cookies": "Strictly Necessary Cookies",
    "strictly necessary": "Strictly Necessary Cookies",
    "necessary": "Strictly Necessary Cookies",
}

TYPE_ORDER = [
    "Targeting Cookies",
    "Performance Cookies",
    "Functional Cookies",
    "Strictly Necessary Cookies",
    "Unknown",
]

# Group colors
GROUP_PALETTE = {
    "Subjected": "#C23B22",   # muted red
    "Non-Subj.": "#1F77B4",   # tab blue
}

# ---------- STYLE (EVEN LARGER FONTS) ----------
mpl.rcParams.update({
    "pdf.fonttype": 42,              # editable text in Illustrator
    "ps.fonttype": 42,
    "figure.dpi": 300,               # hi-DPI PNGs
    "savefig.dpi": 300,
    "axes.linewidth": 2.0,
    "axes.edgecolor": "black",
    "xtick.major.width": 1.8,
    "ytick.major.width": 1.8,
    "font.size": 26,                 # EVEN LARGER base font size
})
sns.set(style="ticks")

# ---------- HELPERS ----------
def _nonempty_series(s: pd.Series) -> pd.Series:
    # True iff value is not NaN and not empty string
    return (~s.isna()) & (s.astype(str).str.strip() != "")

def _norm_category(val: str) -> str:
    if not isinstance(val, str):
        return "Unknown"
    key = re.sub(r"[_\-]+", " ", val.strip().lower())
    return CANON_TYPES_MAP.get(key, "Unknown")

def _norm_group(v: str) -> str:
    """Normalize CCPA subjectivity into two groups: Subjected vs Non-Subj."""
    v = str(v).strip().lower()
    if v == "subjected":
        return "Subjected"
    if v == "subject to ccpa":
        return "Subjected"
    if "subject" in v and "ccpa" in v:
        return "Subjected"
    return "Non-Subj."

def _clean_host(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    if re.match(r'^[a-z]+://', s, flags=re.I):
        s = urlparse(s).netloc
    s = s.split('@')[-1].split(':')[0].split('/')[0]
    s = re.sub(r'^www\d*\.', '', s, flags=re.I)
    return s.lower().strip('.')

def _ensure_cookie_type(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure df has a 'Cookie Type' column using harmonized categories.
    Uses df['category'] from final_default_state_comprehensive_updated.csv.
    """
    df = df.copy()
    if "Cookie Type" not in df.columns:
        if "category" not in df.columns:
            raise ValueError("Need 'Cookie Type' or 'category' in the dataframe.")
        df["Cookie Type"] = df["category"].map(_norm_category)
    else:
        df["Cookie Type"] = df["Cookie Type"].astype(str)
        df["Cookie Type"] = np.where(
            df["Cookie Type"].str.strip().str.lower().eq("other"),
            "Unknown",
            df["Cookie Type"],
        )
    return df

def _ensure_site(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure we have a normalized site identifier 'site_clean'.
    Uses the 'website' column from the CSV.
    """
    if "site_clean" in df.columns:
        return df
    if "website" not in df.columns:
        raise ValueError("Need 'site_clean' or 'website' column.")
    df = df.copy()
    df["site_clean"] = df["website"].astype(str).map(_clean_host)
    return df

def _ensure_presence_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure presence indicator columns present_<config> exist for all RAW_CONFIGS.
    Presence: config column is non-null and non-empty (NaNs from CSV are preserved).
    """
    df = df.copy()
    for raw, _ in RAW_CONFIGS:
        pres = f"present_{raw}"
        if pres not in df.columns:
            if raw not in df.columns:
                raise ValueError(f"Missing column '{raw}' in the dataframe.")
            df[pres] = _nonempty_series(df[raw]).astype(int)
        else:
            df[pres] = pd.to_numeric(df[pres], errors="coerce").fillna(0).astype(int)
    return df

def _ensure_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure a 'Group' column exists, derived from 'ccpa' or 'CCPA_Category'.
    """
    if "Group" in df.columns:
        return df
    df = df.copy()
    if "ccpa" in df.columns:
        df["Group"] = df["ccpa"].map(_norm_group)
    elif "CCPA_Category" in df.columns:
        df["Group"] = df["CCPA_Category"].map(_norm_group)
    else:
        raise ValueError("Need 'Group', 'ccpa', or 'CCPA_Category' column.")
    return df

def _melt_all_types_all_configs_with_group(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return long df: site_clean | Cookie Type | Group | Config | Count

    Count = number of cookies of that type on that site present under each config.
    """
    df = _ensure_cookie_type(df)
    df = _ensure_site(df)
    df = _ensure_presence_cols(df)
    df = _ensure_group(df)

    print(f"[INFO] Raw cookies: {len(df):,}")
    print(f"[INFO] Unique sites: {df['site_clean'].nunique():,}")

    present_types = [t for t in TYPE_ORDER if t in set(df["Cookie Type"].unique())]
    base = df[df["Cookie Type"].isin(present_types)].copy()

    parts = []
    for raw, label in RAW_CONFIGS:
        pcol = f"present_{raw}"
        per_site = (
            base.dropna(subset=["site_clean"])
                .groupby(["site_clean", "Cookie Type", "Group"], as_index=False)[pcol]
                .sum()
                .rename(columns={pcol: "Count"})
        )
        per_site["Config"] = label
        parts.append(per_site[["site_clean", "Cookie Type", "Group", "Config", "Count"]])

    long_df = pd.concat(parts, ignore_index=True)
    long_df["Cookie Type"] = pd.Categorical(long_df["Cookie Type"], present_types, ordered=True)
    long_df["Config"] = pd.Categorical(long_df["Config"], [lbl for _, lbl in RAW_CONFIGS], ordered=True)
    long_df["Group"] = pd.Categorical(long_df["Group"], ["Subjected", "Non-Subj."], ordered=True)

    print(f"[INFO] Long DF rows (site x type x group x config): {len(long_df):,}")
    print(f"[INFO] Sites in long DF: {long_df['site_clean'].nunique():,}")
    return long_df

# ---------- PLOTTING ----------
def _pretty_cfg_labels(order):
    # Force a clean two-line label for Block 3rd-party, others as-is
    pretty = []
    for lbl in order:
        if "3rd-party" in lbl:
            pretty.append("Block\n3rd-party")
        else:
            pretty.append(lbl)
    return pretty

def plot_split_violin_subject_vs_non(long_df: pd.DataFrame,
                                     fname="split_violin_subject_vs_non",
                                     ylim=(0, 30)):
    """
    High-quality split-violin faceted by Cookie Type, x = Config,
    split halves = CCPA Group (Subjected vs Non-Subj.).

    UPDATED: Minimal whitespace, larger figures, horizontal legend at top, larger fonts.
    """
    cfg_order = [lbl for _, lbl in RAW_CONFIGS]
    type_order = [t for t in TYPE_ORDER if t in set(long_df["Cookie Type"].unique())]
    group_order = ["Subjected", "Non-Subj."]

    df = long_df.copy()
    df = df[df["Cookie Type"].isin(type_order)]
    df["Config"] = pd.Categorical(df["Config"], cfg_order, ordered=True)
    df["Group"] = pd.Categorical(df["Group"], group_order, ordered=True)
    df["Cookie Type"] = pd.Categorical(df["Cookie Type"], type_order, ordered=True)

    # === MUCH LARGER FIGURE SIZE TO ACCOMMODATE LEGEND ===
    # Make each facet wider and taller, plus extra height for legend
    width = max(18.0, 5.5 * len(type_order))  # INCREASED width
    height = 9.0                                # INCREASED height for legend and labels

    g = sns.catplot(
        data=df,
        x="Config", y="Count",
        hue="Group", split=True,
        kind="violin",
        inner="quartile", cut=0,
        density_norm="width",
        linewidth=1.6,
        width=0.5,
        hue_order=group_order,
        col="Cookie Type", col_order=type_order,
        sharex=False, sharey=True,
        height=height,
        aspect=(width / len(type_order) / height * 1.2),
        palette=GROUP_PALETTE,
    )

    pretty_x = _pretty_cfg_labels(cfg_order)

    for ax in g.axes.flat:
        # Grid with good visibility
        ax.grid(True, axis="y", linewidth=1.2, alpha=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.set_xlabel("")
        ax.set_ylabel("Cookies per website", fontsize=34)  # LARGER for readability
        ax.tick_params(axis="x", labelsize=28)              # LARGER for readability
        ax.tick_params(axis="y", labelsize=28, direction="in", length=6, width=1.8, color="black")

        # Fix ticks before labels
        ax.set_xticks(range(len(cfg_order)))
        ax.set_xticklabels(pretty_x, rotation=30, ha="right")

        if ylim:
            ax.set_ylim(ylim)

        # Clean facet titles, LARGER font for readability
        ax.set_title(ax.get_title().replace("Cookie Type = ", ""), fontsize=32, fontweight='bold')

        # Increase alpha of violins
        for coll in ax.collections:
            try:
                coll.set_alpha(0.95)
            except Exception:
                pass

    # === ADJUST SUBPLOT POSITIONING TO RESERVE SPACE FOR LEGEND ===
    g.fig.subplots_adjust(
        top=0.82,      # Leave much more space at top for legend
        bottom=0.20,   # Leave more room at bottom for larger rotated x-labels
        left=0.05,     # Tight left margin
        right=0.99,    # Tight right margin
        wspace=0.12    # MINIMAL spacing between facets
    )

    # === HORIZONTAL LEGEND AT TOP USING SUPTITLE ===
    # Use matplotlib patches to create manual legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D

    # Remove default legend if exists
    if g._legend is not None:
        g._legend.remove()

    # Create legend elements manually
    legend_elements = [
        Patch(facecolor=GROUP_PALETTE["Subjected"], label='Subjected'),
        Patch(facecolor=GROUP_PALETTE["Non-Subj."], label='Non-Subj.')
    ]

    # Add legend at a fixed position using figure.legend
    # Place it in the larger space at top
    leg = g.fig.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 0.90),  # Position in the larger top space
        ncol=2,
        fontsize=28,
        frameon=False,
        columnspacing=4.0,
        handlelength=2.0,
        handleheight=1.5,
    )
    for text in leg.get_texts():
        text.set_fontweight('bold')

    # Overlay MEDIAN diamonds (slightly larger)
    grouped = df.groupby(["Cookie Type", "Config", "Group"])["Count"].median().reset_index()
    grouped["Config"] = pd.Categorical(grouped["Config"], cfg_order, ordered=True)
    grouped["Group"] = pd.Categorical(grouped["Group"], group_order, ordered=True)

    facet_axes = {ax.get_title(): ax for ax in g.axes.flat}
    jitter = {"Subjected": -0.28, "Non-Subj.": 0.28}
    for _, row in grouped.iterrows():
        cookie_type = str(row["Cookie Type"])
        ax = facet_axes[cookie_type]
        x_idx = list(df["Config"].cat.categories).index(row["Config"])
        x = x_idx + jitter[str(row["Group"])]
        ax.plot(
            [x], [row["Count"]],
            marker="D", markersize=7.5,  # Slightly larger
            color="black", zorder=5
        )

    pdf_path = os.path.join(OUTDIR, f"{fname}.pdf")
    png_path = os.path.join(OUTDIR, f"{fname}.png")
    # Save WITHOUT bbox_inches="tight" to preserve legend and suptitle
    g.fig.savefig(pdf_path, dpi=300)
    g.fig.savefig(png_path, dpi=300)
    plt.close(g.fig)
    print(f"[SAVED] {pdf_path}")
    print(f"[SAVED] {png_path}")

# ---------- WIRING ----------
if __name__ == "__main__":
    # low_memory=False to avoid DtypeWarning
    raw = pd.read_csv("../Analysis/final_default_state_comprehensive_reclassified.csv", low_memory=False)
    long_df = _melt_all_types_all_configs_with_group(raw)
    plot_split_violin_subject_vs_non(long_df, ylim=(0, 30))
