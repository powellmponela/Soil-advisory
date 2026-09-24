from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.cm import ScalarMappable

try:
    import geopandas as gpd
except ImportError:
    gpd = None

ROOT = Path(r"D:\dss\SOIL ADVISORY")
OUT = ROOT / "outputs" / "spatial_extrapolation"
INPUT = OUT / "western_n_demand_savings_pixels.csv"
BOUNDARY = ROOT / "Data" / "boundary" / "ward_level_boundary.gpkg"
MAPDIR = OUT / "maps_ae_gains"
MAPDIR.mkdir(parents=True, exist_ok=True)

# Fixed scales preserve comparability across strategies and target-yield frames.
AE_RANGE = (0, 60)                 # kg grain kg-1 N
PFP_RANGE = (0, 180)               # kg grain kg-1 mineral N
GAIN_0PK_RANGE = (0, 6)            # t ha-1
DIFF_GR_RANGE = (-2.5, 2.5)        # t ha-1
N_CHANGE_RANGE = (-100, 100)       # kg N ha-1; negative=reduction, positive=increase
N_REQUIRED_RANGE = (0, 240)        # kg N ha-1

# Sequential maps use a light-to-dark scale. Diverging maps are centred on zero.
SEQ_CMAP = "YlGnBu"
DIV_CMAP = "RdBu_r"
POINT_SIZE = 18
N_COLS = 3

# Fixed strategy order so every figure has the same panel positions.
# FYM, PCU and UDP are explicitly retained in the comparison frame.
STRATEGY_ORDER = [
    "GR",
    "N60",
    "N180",
    "N210",
    "TIMING_V6_V10",
    "FYM_N60",
    "PCU_N120",
    "PCU_N60",
    "UDP_N78",
]

AE_STRATEGIES = [
    "GR",
    "N60",
    "N180",
    "N210",
    "TIMING_V6_V10",
]

PFP_STRATEGIES = [
    "FYM_N60",
    "PCU_N120",
    "PCU_N60",
    "UDP_N78",
]

STRATEGY_LABELS = {
    "GR": "GR (N120)",
    "N60": "N60",
    "N180": "N180",
    "N210": "N210",
    "TIMING_V6_V10": "Timing V6/V10 (N120)",
    "FYM_N60": "FYM + N60",
    "PCU_N120": "PCU N120",
    "PCU_N60": "PCU N60",
    "UDP_N78": "UDP N78",
}


def load_boundary():
    if gpd is None or not BOUNDARY.exists():
        return None
    try:
        b = gpd.read_file(BOUNDARY)
        if b.crs is not None and str(b.crs).lower() != "epsg:4326":
            b = b.to_crs(4326)
        return b
    except Exception:
        return None


def global_extent(df):
    q = df.dropna(subset=["lon", "lat"])
    return (
        q["lon"].min() - 0.05,
        q["lon"].max() + 0.05,
        q["lat"].min() - 0.05,
        q["lat"].max() + 0.05,
    )


def plot_boundary(ax, boundary, extent):
    if boundary is None:
        return
    xmin, xmax, ymin, ymax = extent
    try:
        bb = boundary.cx[xmin:xmax, ymin:ymax]
        if not bb.empty:
            bb.boundary.plot(ax=ax, linewidth=0.22, color="0.78", zorder=1)
    except Exception:
        pass


def panel_frame(
    df,
    target,
    value_col,
    title_prefix,
    cbar_label,
    out_file,
    vmin,
    vmax,
    cmap=SEQ_CMAP,
    centered=False,
    strategies=None,
):
    q0 = df[(df["target_yield_t_ha"] == target) & df["environmental_support"].fillna(False)].copy()
    q0 = q0.dropna(subset=["lon", "lat"])
    if q0.empty:
        return

    # Show only strategies for which the requested metric was actually modelled.
    if strategies is None:
        strategies = [
            s for s in STRATEGY_ORDER
            if s in set(q0["strategy"].dropna().astype(str))
            and q0.loc[q0["strategy"] == s, value_col].notna().any()
        ]
    else:
        strategies = [
            s for s in strategies
            if s in set(q0["strategy"].dropna().astype(str))
            and q0.loc[q0["strategy"] == s, value_col].notna().any()
        ]

    if not strategies:
        return

    n = len(strategies)
    # Compact layout determined by the number of modelled strategies.
    # Five panels: 3 + 2; four panels: 2 x 2; 6-9 panels: 3 columns.
    if n <= 4:
        ncols = 2
    else:
        ncols = 3
    nrows = math.ceil(n / ncols)

    extent = global_extent(q0)
    boundary = load_boundary()

    # Figure height scales with actual rows so empty space is not reserved.
    fig_width = 14.8 if ncols == 3 else 10.8
    fig_height = 3.55 * nrows + 1.55
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(fig_width, fig_height),
        squeeze=False,
        sharex=True,
        sharey=True,
    )

    norm = (
        TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
        if centered
        else Normalize(vmin=vmin, vmax=vmax)
    )

    for i, (ax, strategy) in enumerate(zip(axes.flat, strategies)):
        q = q0[q0["strategy"] == strategy].dropna(subset=[value_col]).copy()
        plot_boundary(ax, boundary, extent)

        if not q.empty:
            ax.scatter(
                q["lon"],
                q["lat"],
                c=q[value_col],
                cmap=cmap,
                norm=norm,
                s=POINT_SIZE,
                marker="s",
                linewidths=0,
                zorder=2,
            )

        ax.set_title(STRATEGY_LABELS.get(strategy, strategy), fontsize=11, fontweight="bold")
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_aspect("equal", adjustable="box")
        ax.tick_params(labelsize=8)

        # Only outer panels carry tick labels; the figure has shared axis labels.
        row = i // ncols
        col = i % ncols
        if col != 0:
            ax.tick_params(labelleft=False)
        if row != nrows - 1:
            ax.tick_params(labelbottom=False)

    for ax in axes.flat[n:]:
        ax.set_visible(False)

    # Shared figure title and axis labels.
    fig.suptitle(
        f"{title_prefix} | target {target:.1f} t ha$^{{-1}}$",
        fontsize=15,
        fontweight="bold",
        y=0.975,
    )

    # Tight layout for the actual number of rows, with dedicated space below
    # for shared longitude label and compact legend.
    bottom_margin = 0.18 if nrows == 2 else 0.15
    fig.subplots_adjust(
        left=0.060,
        right=0.985,
        top=0.91,
        bottom=bottom_margin,
        wspace=0.08,
        hspace=0.08,
    )

    fig.supxlabel("Longitude", fontsize=10, y=0.105 if nrows == 2 else 0.085)
    fig.supylabel("Latitude", fontsize=10, x=0.020)

    sm = ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    # Compact centred colorbar, scaled to figure width and kept clear of axis labels.
    cbar_width = 0.44 if ncols == 3 else 0.52
    cbar_left = (1.0 - cbar_width) / 2.0
    cbar_bottom = 0.045 if nrows == 2 else 0.030
    cax = fig.add_axes([cbar_left, cbar_bottom, cbar_width, 0.022])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.ax.tick_params(labelsize=9, length=3, pad=3)
    cbar.set_label(cbar_label, fontsize=10, labelpad=5)

    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_equivalent_yield_summary(df):
    s = (
        df[df["environmental_support"].fillna(False)]
        .groupby("strategy", dropna=False)
        .agg(
            tested_N_rate_kg_ha=("strategy_N_rate_kg_ha", "first"),
            tested_N_change_vs_GR_kg_ha=("tested_N_change_vs_GR_kg_ha", "first"),
            median_N_required_for_GR_equivalent_yield_kg_ha=(
                "N_required_for_GR_equivalent_yield_kg_ha",
                "median",
            ),
            median_N_change_at_GR_equivalent_yield_kg_ha=(
                "N_change_at_GR_equivalent_yield_kg_ha",
                "median",
            ),
            median_N_reduction_at_GR_equivalent_yield_kg_ha=(
                "N_reduction_at_GR_equivalent_yield_kg_ha",
                "median",
            ),
            median_N_increase_at_GR_equivalent_yield_kg_ha=(
                "N_increase_at_GR_equivalent_yield_kg_ha",
                "median",
            ),
        )
        .reset_index()
    )

    # Keep the same agronomic strategy order in the summary output and graph.
    order = {s: i for i, s in enumerate(STRATEGY_ORDER)}
    s["_order"] = s["strategy"].map(order).fillna(999)
    s = s.sort_values("_order").drop(columns="_order")
    s.to_csv(OUT / "western_strategy_equivalent_yield_N_change_vs_GR.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = np.arange(len(s))
    vals = s["median_N_change_at_GR_equivalent_yield_kg_ha"].to_numpy(float)
    ax.bar(x, vals)
    ax.axhline(0, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [STRATEGY_LABELS.get(v, v) for v in s["strategy"]],
        rotation=40,
        ha="right",
    )
    ax.set_ylabel("N change for GR-equivalent yield (kg N ha$^{-1}$)")
    ax.set_title("Estimated N reduction/increase required to achieve GR-equivalent yield")
    ax.text(
        0.01,
        0.98,
        "Negative = less N required; positive = more N required",
        transform=ax.transAxes,
        va="top",
    )
    fig.tight_layout()
    fig.savefig(
        MAPDIR / "strategy_N_change_at_GR_equivalent_yield.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Run 5b_predict_western_n_demand_savings.py first: {INPUT}")

    df = pd.read_csv(INPUT)
    df["predicted_yield_gain_over_0PK_t_ha"] = df["predicted_yield_gain_over_0PK_kg_ha"] / 1000.0
    df["predicted_yield_difference_from_GR_t_ha"] = df["predicted_yield_difference_from_GR_kg_ha"] / 1000.0

    required = [
        "target_yield_t_ha",
        "strategy",
        "environmental_support",
        "predicted_AE_N_kg_grain_per_kg_N",
        "predicted_yield_gain_over_0PK_t_ha",
        "predicted_yield_difference_from_GR_t_ha",
        "strategy_N_rate_kg_ha",
        "tested_N_change_vs_GR_kg_ha",
        "N_required_for_GR_equivalent_yield_kg_ha",
        "N_change_at_GR_equivalent_yield_kg_ha",
        "reference_N_demand_kg_ha",
        "N_required_for_same_target_yield_kg_ha",
        "N_change_for_same_target_yield_kg_ha",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing columns from Stage 5b: " + ", ".join(missing))

    # Report which agreed strategies are actually present in Stage 5b output.
    present = set(df["strategy"].dropna().astype(str).unique())
    print("Strategies present in Stage 5b:", ", ".join(sorted(present)))
    missing_strategies = [s for s in STRATEGY_ORDER if s not in present]
    if missing_strategies:
        print("Not modelled / absent from Stage 5b:", ", ".join(missing_strategies))

    make_equivalent_yield_summary(df)

    targets = sorted(pd.to_numeric(df["target_yield_t_ha"], errors="coerce").dropna().unique())
    for target in targets:
        tag = str(target).replace(".", "p")
        panel_frame(
            df,
            target,
            "predicted_AE_N_kg_grain_per_kg_N",
            "Predicted AE-N by strategy",
            "AE-N (kg grain kg$^{-1}$ N)",
            MAPDIR / f"AE_N_all_strategies_target_{tag}.png",
            *AE_RANGE,
            cmap=SEQ_CMAP,
            centered=False,
            strategies=AE_STRATEGIES,
        )
        if "predicted_PFP_N_kg_grain_per_kg_N" in df.columns:
            panel_frame(
                df,
                target,
                "predicted_PFP_N_kg_grain_per_kg_N",
                "Predicted PFP-N for FYM, PCU and UDP strategies",
                "PFP-N (kg grain kg$^{-1}$ mineral N)",
                MAPDIR / f"PFP_N_PCU_FYM_UDP_target_{tag}.png",
                *PFP_RANGE,
                cmap=SEQ_CMAP,
                centered=False,
                strategies=PFP_STRATEGIES,
            )

        panel_frame(
            df,
            target,
            "predicted_yield_gain_over_0PK_t_ha",
            "Predicted yield gain above 0PK by strategy",
            "Yield gain above 0PK (t ha$^{-1}$)",
            MAPDIR / f"yield_gain_0PK_all_strategies_target_{tag}.png",
            *GAIN_0PK_RANGE,
            cmap=SEQ_CMAP,
            centered=False,
        )
        panel_frame(
            df,
            target,
            "predicted_yield_difference_from_GR_t_ha",
            "Predicted yield difference from GR by strategy",
            "Yield difference from GR (t ha$^{-1}$)",
            MAPDIR / f"yield_difference_GR_all_strategies_target_{tag}.png",
            *DIFF_GR_RANGE,
            cmap=DIV_CMAP,
            centered=True,
        )
        panel_frame(
            df,
            target,
            "N_required_for_same_target_yield_kg_ha",
            "N required to achieve the same target yield by strategy",
            "N required for same target yield (kg N ha$^{-1}$)",
            MAPDIR / f"N_required_same_yield_all_strategies_target_{tag}.png",
            *N_REQUIRED_RANGE,
            cmap=SEQ_CMAP,
            centered=False,
        )
        panel_frame(
            df,
            target,
            "N_change_for_same_target_yield_kg_ha",
            "N reduction/increase for the same target yield by strategy",
            "N change for same target yield (kg N ha$^{-1}$; negative = reduction)",
            MAPDIR / f"N_change_same_yield_all_strategies_target_{tag}.png",
            *N_CHANGE_RANGE,
            cmap=DIV_CMAP,
            centered=True,
        )

    supported = df[df["environmental_support"].fillna(False)].copy()
    cols = [
        "province",
        "district",
        "palika",
        "lat",
        "lon",
        "target_yield_t_ha",
        "strategy",
        "strategy_N_rate_kg_ha",
        "tested_N_change_vs_GR_kg_ha",
        "predicted_AE_N_kg_grain_per_kg_N",
        "predicted_AE_N_ratio_to_GR",
        "predicted_yield_gain_over_0PK_t_ha",
        "predicted_yield_difference_from_GR_t_ha",
        "predicted_yield_retention_fraction",
        "N_required_for_GR_equivalent_yield_kg_ha",
        "N_change_at_GR_equivalent_yield_kg_ha",
        "N_reduction_at_GR_equivalent_yield_kg_ha",
        "N_increase_at_GR_equivalent_yield_kg_ha",
        "reference_N_demand_kg_ha",
        "N_required_for_same_target_yield_kg_ha",
        "N_change_for_same_target_yield_kg_ha",
        "N_reduction_for_same_target_yield_kg_ha",
        "N_increase_for_same_target_yield_kg_ha",
        "N_change_for_same_target_yield_pct",
        "retains_95pct_GR",
        "environmental_support",
    ]
    supported[[c for c in cols if c in supported.columns]].to_csv(
        OUT / "western_ae_gains_map_table.csv", index=False
    )

    print(f"Comparable multi-strategy map frames saved to: {MAPDIR}")
    print(OUT / "western_ae_gains_map_table.csv")
    print(OUT / "western_strategy_equivalent_yield_N_change_vs_GR.csv")


if __name__ == "__main__":
    main()
