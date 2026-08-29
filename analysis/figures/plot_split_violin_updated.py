# Usage: python plot_split_violin_updated.py  |  Split-violin of cookie categories by CCPA subjectivity (re-verified labels).
import os, re
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt
from urllib.parse import urlparse

BASE = os.environ.get("PRIVAUDIT_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = f"{BASE}/figures_output"
os.makedirs(OUTDIR, exist_ok=True)

RAW_CONFIGS = [
    ("initial_cookies", "Default"),
    ("do_not_track", "DNT"),
    ("block_3rd_party", "Block 3rd-party"),
    ("ublock", "uBlock"),
    ("gpc_enabled", "GPC"),
]

CANON_TYPES_MAP = {

    "targeting": "Targeting Cookies",
    "targeting cookies": "Targeting Cookies",
    "advertising": "Targeting Cookies",

    "performance": "Performance Cookies",
    "performance cookies": "Performance Cookies",
    "analytics": "Performance Cookies",

    "functional": "Functional Cookies",
    "functional cookies": "Functional Cookies",

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

GROUP_PALETTE = {
    "CCPA-Subject": "#C23B22",
    "CCPA-Not-Subject": "#1F77B4",
}

mpl.rcParams.update({
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.linewidth": 2.0,
    "axes.edgecolor": "black",
    "xtick.major.width": 1.8,
    "ytick.major.width": 1.8,
    "font.size": 26,
})
sns.set(style="ticks")

def _nonempty_series(s: pd.Series) -> pd.Series:

    return (~s.isna()) & (s.astype(str).str.strip() != "")

def _norm_category(val: str) -> str:
    if not isinstance(val, str):
        return "Unknown"
    key = re.sub(r"[_\-]+", " ", val.strip().lower())
    return CANON_TYPES_MAP.get(key, "Unknown")

def _norm_group(v: str) -> str:
    v = str(v).strip().lower()
    if v == "subjected":
        return "CCPA-Subject"
    if v == "subject to ccpa":
        return "CCPA-Subject"
    if "subject" in v and "ccpa" in v:
        return "CCPA-Subject"
    return "CCPA-Not-Subject"

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
    if "site_clean" in df.columns:
        return df
    if "website" not in df.columns:
        raise ValueError("Need 'site_clean' or 'website' column.")
    df = df.copy()
    df["site_clean"] = df["website"].astype(str).map(_clean_host)
    return df

def _ensure_presence_cols(df: pd.DataFrame) -> pd.DataFrame:
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
    long_df["Group"] = pd.Categorical(long_df["Group"], ["CCPA-Subject", "CCPA-Not-Subject"], ordered=True)

    print(f"[INFO] Long DF rows (site x type x group x config): {len(long_df):,}")
    print(f"[INFO] Sites in long DF: {long_df['site_clean'].nunique():,}")
    return long_df

def _pretty_cfg_labels(order):

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
    cfg_order = [lbl for _, lbl in RAW_CONFIGS]
    type_order = [t for t in TYPE_ORDER if t in set(long_df["Cookie Type"].unique())]
    group_order = ["CCPA-Subject", "CCPA-Not-Subject"]

    df = long_df.copy()
    df = df[df["Cookie Type"].isin(type_order)]
    df["Config"] = pd.Categorical(df["Config"], cfg_order, ordered=True)
    df["Group"] = pd.Categorical(df["Group"], group_order, ordered=True)
    df["Cookie Type"] = pd.Categorical(df["Cookie Type"], type_order, ordered=True)

    width = max(18.0, 5.5 * len(type_order))
    height = 9.0

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

        ax.grid(True, axis="y", linewidth=1.2, alpha=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.set_xlabel("")
        ax.set_ylabel("Cookies per website", fontsize=34)
        ax.tick_params(axis="x", labelsize=28)
        ax.tick_params(axis="y", labelsize=28, direction="in", length=6, width=1.8, color="black")

        ax.set_xticks(range(len(cfg_order)))
        ax.set_xticklabels(pretty_x, rotation=30, ha="right")

        if ylim:
            ax.set_ylim(ylim)

        ax.set_title(ax.get_title().replace("Cookie Type = ", ""), fontsize=32, fontweight='bold')

        for coll in ax.collections:
            try:
                coll.set_alpha(0.95)
            except Exception:
                pass

    g.fig.subplots_adjust(
        top=0.82,
        bottom=0.20,
        left=0.05,
        right=0.99,
        wspace=0.12
    )

    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D

    if g._legend is not None:
        g._legend.remove()

    legend_elements = [
        Patch(facecolor=GROUP_PALETTE["CCPA-Subject"], label='CCPA-Subject'),
        Patch(facecolor=GROUP_PALETTE["CCPA-Not-Subject"], label='CCPA-Not-Subject')
    ]

    leg = g.fig.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 0.90),
        ncol=2,
        fontsize=28,
        frameon=False,
        columnspacing=4.0,
        handlelength=2.0,
        handleheight=1.5,
    )
    for text in leg.get_texts():
        text.set_fontweight('bold')

    grouped = df.groupby(["Cookie Type", "Config", "Group"])["Count"].median().reset_index()
    grouped["Config"] = pd.Categorical(grouped["Config"], cfg_order, ordered=True)
    grouped["Group"] = pd.Categorical(grouped["Group"], group_order, ordered=True)

    facet_axes = {ax.get_title(): ax for ax in g.axes.flat}
    jitter = {"CCPA-Subject": -0.28, "CCPA-Not-Subject": 0.28}
    for _, row in grouped.iterrows():
        cookie_type = str(row["Cookie Type"])
        ax = facet_axes[cookie_type]
        x_idx = list(df["Config"].cat.categories).index(row["Config"])
        x = x_idx + jitter[str(row["Group"])]
        ax.plot(
            [x], [row["Count"]],
            marker="D", markersize=7.5,
            color="black", zorder=5
        )

    pdf_path = os.path.join(OUTDIR, f"{fname}.pdf")
    png_path = os.path.join(OUTDIR, f"{fname}.png")

    g.fig.savefig(pdf_path, dpi=300)
    g.fig.savefig(png_path, dpi=300)
    plt.close(g.fig)
    print(f"[SAVED] {pdf_path}")
    print(f"[SAVED] {png_path}")

if __name__ == "__main__":

    raw = pd.read_csv(f"{BASE}/data/final_default_state_comprehensive_NEWLABELS.csv", low_memory=False)
    long_df = _melt_all_types_all_configs_with_group(raw)
    plot_split_violin_subject_vs_non(long_df, ylim=(0, 30))
