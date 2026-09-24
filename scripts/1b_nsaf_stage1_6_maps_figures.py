from __future__ import annotations

r"""
NSAF maize Stage 1-6 maps and individual-site distribution figures.

Project root
------------
D:\dss\SOIL ADVISORY

Boundary
--------
D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

Mapping rules
-------------
- EPSG:4326 longitude/latitude degrees.
- Ward polygons are restricted to districts represented in each
  study/year/variety block.
- Map extent is cropped to those study districts.
- Trial points are measured observations only.
- No DSM interpolation/extrapolation is performed.

Run
---
python .\scripts\1b_nsaf_stage1_6_maps_figures.py
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

SITE_FILE = OUTPUTS / "nsaf_stage1_6_study_year_site.csv"
TARGET_FILE = OUTPUTS / "nsaf_stage5_n_rate_target_by_study_year_site.csv"

BOUNDARY_FILE = ROOT / "Data" / "boundary" / "ward_level_boundary.gpkg"

FIG_DIR = OUTPUTS / "figures" / "stage1_6"
MAP_DIR = OUTPUTS / "maps" / "stage1_6"
MANIFEST = OUTPUTS / "nsaf_stage1_6_figure_manifest.csv"

FIG_DIR.mkdir(parents=True, exist_ok=True)
MAP_DIR.mkdir(parents=True, exist_ok=True)

LAT_CANDIDATES = [
    "latitude",
    "lat",
    "latitude_dd",
    "lat_dd",
    "y_coord",
    "ycoord",
]
LON_CANDIDATES = [
    "longitude",
    "lon",
    "lng",
    "long",
    "longitude_dd",
    "lon_dd",
    "x_coord",
    "xcoord",
]

DISTRICT_ALIASES = {
    "kavre": {
        "kavre",
        "kavrepalanchok",
        "kavrepalanchowk",
    },
}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def clean_filename(value):
    text = re.sub(r"[^\w\-]+", "_", str(value), flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:140] or "unknown"


def first_column(columns, candidates):
    lookup = {str(c).strip().lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def normalize_site(s):
    return (
        s.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def valid_latlon(lat, lon):
    return (
        lat.notna()
        & lon.notna()
        & lat.between(-90, 90)
        & lon.between(-180, 180)
    )


def norm_name(value):
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    text = text.replace("district", "")
    return text


def district_tokens(name):
    base = norm_name(name)
    values = {base}

    for key, aliases in DISTRICT_ALIASES.items():
        if base == norm_name(key):
            values.update(norm_name(x) for x in aliases)

    return values


def load_stage():
    if not SITE_FILE.exists():
        raise FileNotFoundError(
            f"Missing:\n{SITE_FILE}\n\n"
            "Run first:\n"
            "python .\\scripts\\run_nsaf_stage1_6.py"
        )

    d = pd.read_csv(SITE_FILE)
    d["year"] = num(d["year"]).astype("Int64")
    d["site_key"] = normalize_site(d["site"])
    return d


def coordinate_lookup_from_frame(df, source_name):
    lat_col = first_column(df.columns, LAT_CANDIDATES)
    lon_col = first_column(df.columns, LON_CANDIDATES)

    if lat_col is None or lon_col is None or "site" not in df.columns:
        return pd.DataFrame()

    x = df.copy()
    x["latitude"] = num(x[lat_col])
    x["longitude"] = num(x[lon_col])
    x["site_key"] = normalize_site(x["site"])

    if "year" in x.columns:
        x["year"] = num(x["year"]).astype("Int64")
    else:
        x["year"] = pd.Series(pd.NA, index=x.index, dtype="Int64")

    x = x[
        valid_latlon(
            x["latitude"],
            x["longitude"],
        )
    ].copy()

    if x.empty:
        return pd.DataFrame()

    out = (
        x.groupby(
            ["year", "site_key"],
            as_index=False,
            dropna=False,
        )
        .agg(
            latitude=("latitude", "median"),
            longitude=("longitude", "median"),
            n_coordinate_rows=("site_key", "size"),
        )
    )

    out["coordinate_source"] = source_name
    return out


def find_coordinates(stage):
    # Use coordinates in Stage table if present.
    lookup = coordinate_lookup_from_frame(
        stage,
        SITE_FILE.name,
    )
    if not lookup.empty:
        return lookup

    priority = [
        OUTPUTS / "merged_maize_trials_carob_like.csv",
        OUTPUTS / "maize_cimmyt_plot_results.csv",
        OUTPUTS / "maize_2019_demo_plot_results.csv",
        OUTPUTS / "external_fp_validation_results.csv",
    ]

    candidates = [p for p in priority if p.exists()]

    for p in sorted(OUTPUTS.glob("*.csv")):
        if (
            p not in candidates
            and p != SITE_FILE
            and p != TARGET_FILE
        ):
            candidates.append(p)

    pieces = []

    for p in candidates:
        try:
            d = pd.read_csv(p)
        except Exception:
            continue

        lookup = coordinate_lookup_from_frame(d, p.name)
        if not lookup.empty:
            pieces.append(lookup)

    if not pieces:
        return pd.DataFrame()

    all_coords = pd.concat(pieces, ignore_index=True)

    priority_order = {
        p.name: i for i, p in enumerate(candidates)
    }

    all_coords["priority"] = (
        all_coords["coordinate_source"]
        .map(priority_order)
        .fillna(9999)
    )

    all_coords = (
        all_coords.sort_values(
            ["year", "site_key", "priority"]
        )
        .drop_duplicates(
            ["year", "site_key"],
            keep="first",
        )
        .drop(columns=["priority"])
    )

    return all_coords


def attach_coordinates(stage, lookup):
    d = stage.copy()

    lat_col = first_column(d.columns, LAT_CANDIDATES)
    lon_col = first_column(d.columns, LON_CANDIDATES)

    if lat_col and lon_col:
        d["latitude"] = num(d[lat_col])
        d["longitude"] = num(d[lon_col])
    else:
        d["latitude"] = np.nan
        d["longitude"] = np.nan

    if lookup.empty:
        d["coordinate_source"] = pd.NA
        return d

    d = d.merge(
        lookup,
        on=["year", "site_key"],
        how="left",
        suffixes=("", "_lookup"),
    )

    if "latitude_lookup" in d.columns:
        d["latitude"] = d["latitude"].fillna(
            d["latitude_lookup"]
        )
        d["longitude"] = d["longitude"].fillna(
            d["longitude_lookup"]
        )

    return d


def load_boundary():
    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(
            f"Required ward boundary not found:\n"
            f"{BOUNDARY_FILE}"
        )

    try:
        import geopandas as gpd
    except Exception as exc:
        raise ImportError(
            "geopandas is required for the ward-level maps"
        ) from exc

    gdf = gpd.read_file(BOUNDARY_FILE)

    if gdf.empty:
        raise ValueError(
            f"Boundary file is empty: {BOUNDARY_FILE}"
        )

    gdf = gdf[gdf.geometry.notna()].copy()

    if gdf.crs is None:
        raise ValueError(
            f"Boundary CRS is undefined: {BOUNDARY_FILE}"
        )

    return gdf.to_crs("EPSG:4326")


def find_district_field(gdf, study_districts):
    target = set()

    for district in study_districts:
        target.update(district_tokens(district))

    best_col = None
    best_score = 0

    for col in gdf.columns:
        if col == "geometry":
            continue

        vals = gdf[col].dropna()
        if vals.empty:
            continue

        unique_values = {
            norm_name(x)
            for x in vals.astype(str).unique()
        }

        score = len(unique_values.intersection(target))

        if score > best_score:
            best_col = col
            best_score = score

    return best_col, best_score


def boundary_for_study(gdf, study_districts):
    districts = [
        str(x).strip()
        for x in pd.Series(study_districts)
        .dropna()
        .unique()
        if str(x).strip()
    ]

    if not districts:
        return gdf.copy(), None

    field, score = find_district_field(
        gdf,
        districts,
    )

    if field is None or score == 0:
        raise ValueError(
            "Could not identify the district field in "
            f"{BOUNDARY_FILE} for districts {districts}. "
            f"Boundary columns are: {list(gdf.columns)}"
        )

    target = set()

    for district in districts:
        target.update(district_tokens(district))

    mask = (
        gdf[field]
        .astype(str)
        .map(norm_name)
        .isin(target)
    )

    clipped = gdf[mask].copy()

    if clipped.empty:
        raise ValueError(
            f"No ward polygons matched {districts} "
            f"using field '{field}'."
        )

    return clipped, field


def set_extent(ax, gdf):
    minx, miny, maxx, maxy = gdf.total_bounds

    dx = max(maxx - minx, 0.05)
    dy = max(maxy - miny, 0.05)

    ax.set_xlim(
        minx - max(0.02, dx * 0.04),
        maxx + max(0.02, dx * 0.04),
    )
    ax.set_ylim(
        miny - max(0.02, dy * 0.04),
        maxy + max(0.02, dy * 0.04),
    )


def base_map(ax, boundary):
    # Keep administrative boundaries visually subdued so the agronomic
    # trial-site observations remain the dominant map layer.
    boundary.boundary.plot(
        ax=ax,
        linewidth=0.6,
        color="lightgrey",
        zorder=1,
    )
    set_extent(ax, boundary)
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")


def save_individual_site_map(
    g,
    metric,
    label,
    outfile,
    boundary,
    manifest,
):
    values = num(g[metric])

    x = g[
        values.notna()
        & valid_latlon(
            num(g["latitude"]),
            num(g["longitude"]),
        )
    ].copy()

    if x.empty:
        return

    fig, ax = plt.subplots(figsize=(7.5, 7))

    base_map(ax, boundary)

    scatter = ax.scatter(
        num(x["longitude"]),
        num(x["latitude"]),
        c=num(x[metric]),
        s=55,
        alpha=0.9,
        edgecolors="none",
        zorder=3,
    )

    colorbar = fig.colorbar(
        scatter,
        ax=ax,
        fraction=0.035,
        pad=0.02,
    )
    colorbar.set_label(label)

    for _, row in x.iterrows():
        ax.annotate(
            str(row["site"]).split("|")[-1].strip(),
            (
                float(row["longitude"]),
                float(row["latitude"]),
            ),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=6,
        )

    title = " | ".join([
        str(x["year"].iloc[0]),
        str(x["study"].iloc[0]),
        str(x["variety"].iloc[0]),
        str(x["treatment_role"].iloc[0]),
    ])

    ax.set_title(title, fontsize=10)

    fig.tight_layout()
    fig.savefig(
        outfile,
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    manifest.append({
        "figure_type": "individual_site_map",
        "year": x["year"].iloc[0],
        "study": x["study"].iloc[0],
        "variety": x["variety"].iloc[0],
        "treatment_role": x["treatment_role"].iloc[0],
        "metric": metric,
        "n_sites": x["site"].nunique(),
        "file": str(outfile),
    })


def save_distribution_figure(
    g,
    metric,
    ylabel,
    outfile,
    manifest,
):
    x = g.copy()
    x[metric] = num(x[metric])
    x = x[x[metric].notna()].copy()

    if x.empty:
        return

    role_table = (
        x[["stage", "treatment_role"]]
        .drop_duplicates()
        .sort_values(["stage", "treatment_role"])
    )

    order = role_table["treatment_role"].tolist()
    positions = {
        role: i + 1
        for i, role in enumerate(order)
    }

    fig, ax = plt.subplots(
        figsize=(max(8, len(order) * 1.25), 6.5)
    )

    arrays = [
        x.loc[
            x["treatment_role"].eq(role),
            metric,
        ].dropna().values
        for role in order
    ]

    valid = [
        (i + 1, a)
        for i, a in enumerate(arrays)
        if len(a)
    ]

    if valid:
        ax.boxplot(
            [a for _, a in valid],
            positions=[p for p, _ in valid],
            widths=0.5,
            showfliers=False,
            zorder=1,
        )

    rng = np.random.default_rng(12345)

    for role in order:
        q = x[
            x["treatment_role"].eq(role)
        ].copy()

        if q.empty:
            continue

        jitter = rng.uniform(
            -0.16,
            0.16,
            len(q),
        )

        ax.scatter(
            np.full(
                len(q),
                positions[role],
                dtype=float,
            ) + jitter,
            q[metric],
            s=26,
            alpha=0.80,
            zorder=3,
        )

    title = " | ".join([
        str(x["year"].iloc[0]),
        str(x["study"].iloc[0]),
        str(x["variety"].iloc[0]),
        ylabel,
    ])

    ax.set_title(title, fontsize=10)
    ax.set_ylabel(ylabel)

    ax.set_xticks(
        range(1, len(order) + 1)
    )
    ax.set_xticklabels(
        order,
        rotation=55,
        ha="right",
        fontsize=8,
    )

    ax.grid(
        axis="y",
        alpha=0.2,
        zorder=0,
    )

    fig.tight_layout()
    fig.savefig(
        outfile,
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    manifest.append({
        "figure_type": "individual_site_distribution",
        "year": x["year"].iloc[0],
        "study": x["study"].iloc[0],
        "variety": x["variety"].iloc[0],
        "treatment_role": "all treatments",
        "metric": metric,
        "n_sites": x["site"].nunique(),
        "file": str(outfile),
    })


def save_stage5_maps(
    target,
    coordinate_lookup,
    boundary_lookup,
    manifest,
):
    if target.empty:
        return

    target = target.copy()

    target["year"] = num(
        target["year"]
    ).astype("Int64")

    target["site_key"] = normalize_site(
        target["site"]
    )

    if not coordinate_lookup.empty:
        target = target.merge(
            coordinate_lookup,
            on=["year", "site_key"],
            how="left",
        )
    else:
        target["latitude"] = np.nan
        target["longitude"] = np.nan

    metrics = [
        (
            "selected_N_rate_kg_ha",
            "Selected N rate (kg N/ha)",
        ),
        (
            "N_rate_adjustment_vs_government_reference_kg_ha",
            "N-rate adjustment relative to N120 (kg N/ha)",
        ),
        (
            "potential_mineral_N_reduction_vs_N120_kg_ha",
            "Potential mineral-N reduction (kg N/ha)",
        ),
        (
            "additional_N_requirement_vs_N120_kg_ha",
            "Additional N requirement (kg N/ha)",
        ),
        (
            "relative_yield_to_observed_maximum_pct",
            "Relative yield to observed maximum (%)",
        ),
    ]

    for (study, year, variety), g in target.groupby(
        ["study", "year", "variety"],
        dropna=False,
    ):
        key = (study, year, variety)

        if key not in boundary_lookup:
            continue

        boundary = boundary_lookup[key]

        for metric, label in metrics:
            if metric not in g.columns:
                continue

            q = g[
                num(g[metric]).notna()
                & valid_latlon(
                    num(g["latitude"]),
                    num(g["longitude"]),
                )
            ].copy()

            if q.empty:
                continue

            filename = (
                f"{clean_filename(year)}__"
                f"{clean_filename(study)}__"
                f"{clean_filename(variety)}__"
                f"stage5__"
                f"{clean_filename(metric)}.png"
            )

            outfile = MAP_DIR / filename

            fig, ax = plt.subplots(
                figsize=(7.5, 7)
            )

            base_map(ax, boundary)

            scatter = ax.scatter(
                num(q["longitude"]),
                num(q["latitude"]),
                c=num(q[metric]),
                s=60,
                alpha=0.9,
                edgecolors="none",
            )

            # Horizontal colour scale at the top.
            cax = fig.add_axes([0.28, 0.90, 0.44, 0.022])
            colorbar = fig.colorbar(
                scatter,
                cax=cax,
                orientation="horizontal",
            )
            colorbar.set_label(label, labelpad=4)
            colorbar.ax.xaxis.set_label_position("top")
            colorbar.ax.xaxis.set_ticks_position("bottom")

            for _, row in q.iterrows():
                ax.annotate(
                    str(row["site"]).split("|")[-1].strip(),
                    (
                        float(row["longitude"]),
                        float(row["latitude"]),
                    ),
                    xytext=(3, 3),
                    textcoords="offset points",
                    fontsize=6,
                )

            ax.set_title(
                f"{year} | {study} | {variety} | "
                f"N-rate response",
                fontsize=10,
            )

            fig.tight_layout()
            fig.savefig(
                outfile,
                dpi=220,
                bbox_inches="tight",
            )
            plt.close(fig)

            manifest.append({
                "figure_type": "stage5_n_rate_map",
                "year": year,
                "study": study,
                "variety": variety,
                "treatment_role": "N-rate response",
                "metric": metric,
                "n_sites": q["site"].nunique(),
                "file": str(outfile),
            })



def save_side_by_side_treatment_maps(
    g,
    metric,
    label,
    boundary,
    outfile,
    manifest,
):
    """
    One figure per study x year x variety x outcome.
    Treatments are displayed side by side with a common colour scale.
    """
    x = g.copy()
    x[metric] = num(x[metric])

    x = x[
        x[metric].notna()
        & valid_latlon(
            num(x["latitude"]),
            num(x["longitude"]),
        )
    ].copy()

    if x.empty:
        return

    treatment_order = (
        x[["stage", "N_kg_ha", "treatment_role"]]
        .drop_duplicates()
        .sort_values(
            ["stage", "N_kg_ha", "treatment_role"],
            na_position="last",
        )
        ["treatment_role"]
        .tolist()
    )

    n_treatments = len(treatment_order)

    if n_treatments == 0:
        return

    # Keep comparison compact while retaining all treatments in one figure.
    ncols = min(4, n_treatments)
    nrows = int(np.ceil(n_treatments / ncols))

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(5.0 * ncols, 5.1 * nrows),
        squeeze=False,
    )

    vals = num(x[metric])
    vmin = vals.min()
    vmax = vals.max()

    # Avoid degenerate scale for constant outcomes.
    if pd.notna(vmin) and pd.notna(vmax) and vmin == vmax:
        delta = max(abs(vmin) * 0.02, 1e-9)
        vmin -= delta
        vmax += delta

    scatter_for_colorbar = None

    for i, treatment in enumerate(treatment_order):
        row = i // ncols
        col = i % ncols
        ax = axes[row][col]

        q = x[
            x["treatment_role"].eq(treatment)
        ].copy()

        base_map(ax, boundary)

        scatter = ax.scatter(
            num(q["longitude"]),
            num(q["latitude"]),
            c=num(q[metric]),
            s=48,
            alpha=0.9,
            edgecolors="none",
            vmin=vmin,
            vmax=vmax,
        )

        scatter_for_colorbar = scatter

        for _, site_row in q.iterrows():
            ax.annotate(
                str(site_row["site"]).split("|")[-1].strip(),
                (
                    float(site_row["longitude"]),
                    float(site_row["latitude"]),
                ),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=5.5,
            )

        # Include N rate in panel title where available.
        n_rates = (
            num(q["N_kg_ha"])
            .dropna()
            .unique()
        )

        if len(n_rates) == 1:
            panel_title = (
                f"{treatment}\n"
                f"N = {n_rates[0]:g} kg/ha"
            )
        else:
            panel_title = treatment

        ax.set_title(
            panel_title,
            fontsize=9,
        )

    # Hide unused panels.
    for j in range(n_treatments, nrows * ncols):
        row = j // ncols
        col = j % ncols
        axes[row][col].axis("off")

    study = x["study"].iloc[0]
    year = x["year"].iloc[0]
    variety = x["variety"].iloc[0]

    # Shared horizontal colour scale centred at the top.
    if scatter_for_colorbar is not None:
        cax = fig.add_axes([0.28, 0.905, 0.44, 0.018])
        cbar = fig.colorbar(
            scatter_for_colorbar,
            cax=cax,
            orientation="horizontal",
        )
        cbar.set_label(label, labelpad=4)
        cbar.ax.xaxis.set_label_position("top")
        cbar.ax.xaxis.set_ticks_position("bottom")

    fig.suptitle(
        f"{year} | {study} | {variety}",
        fontsize=12,
        y=0.985,
    )

    fig.subplots_adjust(
        left=0.05,
        right=0.98,
        bottom=0.06,
        top=0.84,
        wspace=0.18,
        hspace=0.25,
    )

    fig.savefig(
        outfile,
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    manifest.append({
        "figure_type": "side_by_side_treatment_maps",
        "year": year,
        "study": study,
        "variety": variety,
        "treatment_role": "all treatments side by side",
        "metric": metric,
        "n_sites": x["site"].nunique(),
        "n_treatments": n_treatments,
        "file": str(outfile),
    })


def save_side_by_side_treatment_distribution(
    g,
    metric,
    ylabel,
    outfile,
    manifest,
):
    """
    Side-by-side treatment distributions within a study/year/variety.
    Each treatment remains a separate category, and every site observation
    is retained as a point.
    """
    x = g.copy()
    x[metric] = num(x[metric])
    x = x[x[metric].notna()].copy()

    if x.empty:
        return

    treatment_table = (
        x[["stage", "N_kg_ha", "treatment_role"]]
        .drop_duplicates()
        .sort_values(
            ["stage", "N_kg_ha", "treatment_role"],
            na_position="last",
        )
    )

    order = treatment_table[
        "treatment_role"
    ].tolist()

    if not order:
        return

    positions = {
        treatment: i + 1
        for i, treatment in enumerate(order)
    }

    fig, ax = plt.subplots(
        figsize=(max(10, len(order) * 1.15), 6.5)
    )

    arrays = [
        x.loc[
            x["treatment_role"].eq(treatment),
            metric,
        ].dropna().values
        for treatment in order
    ]

    valid = [
        (i + 1, values)
        for i, values in enumerate(arrays)
        if len(values)
    ]

    if valid:
        ax.boxplot(
            [values for _, values in valid],
            positions=[position for position, _ in valid],
            widths=0.5,
            showfliers=False,
            zorder=1,
        )

    rng = np.random.default_rng(12345)

    for treatment in order:
        q = x[
            x["treatment_role"].eq(treatment)
        ].copy()

        jitter = rng.uniform(
            -0.16,
            0.16,
            len(q),
        )

        ax.scatter(
            np.full(
                len(q),
                positions[treatment],
                dtype=float,
            ) + jitter,
            q[metric],
            s=24,
            alpha=0.80,
            zorder=3,
        )

    tick_labels = []

    for treatment in order:
        q = x[
            x["treatment_role"].eq(treatment)
        ]

        n_rates = (
            num(q["N_kg_ha"])
            .dropna()
            .unique()
        )

        if len(n_rates) == 1:
            tick_labels.append(
                f"{treatment}\nN={n_rates[0]:g}"
            )
        else:
            tick_labels.append(treatment)

    ax.set_xticks(
        range(1, len(order) + 1)
    )
    ax.set_xticklabels(
        tick_labels,
        rotation=50,
        ha="right",
        fontsize=8,
    )

    ax.set_ylabel(ylabel)
    ax.grid(
        axis="y",
        alpha=0.2,
        zorder=0,
    )

    year = x["year"].iloc[0]
    study = x["study"].iloc[0]
    variety = x["variety"].iloc[0]

    ax.set_title(
        f"{year} | {study} | {variety}\n{ylabel}",
        fontsize=11,
    )

    fig.tight_layout()
    fig.savefig(
        outfile,
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    manifest.append({
        "figure_type": "side_by_side_treatment_distribution",
        "year": year,
        "study": study,
        "variety": variety,
        "treatment_role": "all treatments side by side",
        "metric": metric,
        "n_sites": x["site"].nunique(),
        "n_treatments": len(order),
        "file": str(outfile),
    })


def main():
    stage = load_stage()

    coordinate_lookup = find_coordinates(
        stage
    )

    stage = attach_coordinates(
        stage,
        coordinate_lookup,
    )

    ward_boundary = load_boundary()

    boundary_lookup = {}
    boundary_metadata = []

    for (study, year, variety), g in stage.groupby(
        ["study", "year", "variety"],
        dropna=False,
    ):
        districts = sorted(
            g["adm1"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        clipped, field = boundary_for_study(
            ward_boundary,
            districts,
        )

        boundary_lookup[
            (study, year, variety)
        ] = clipped

        boundary_metadata.append({
            "study": study,
            "year": year,
            "variety": variety,
            "districts": ";".join(districts),
            "boundary_district_field": field,
            "n_ward_polygons": len(clipped),
        })

    manifest = []

    map_metrics = [
        (
            "mean_yield_kg_ha",
            "Yield (kg/ha)",
        ),
        (
            "yield_response_to_N_kg_ha",
            "Yield response to N (kg/ha)",
        ),
        (
            "AE_N_kg_grain_per_kg_N",
            "Agronomic efficiency of N, AE-N (kg grain/kg N)",
        ),
        (
            "PFP_N_kg_grain_per_kg_N",
            "Partial factor productivity of N, PFP-N (kg grain/kg N)",
        ),
        (
            "relative_yield_to_government_reference_pct",
            "Relative yield to N120-P-K reference (%)",
        ),
        (
            "potential_mineral_N_reduction_kg_ha",
            "Potential mineral-N reduction (kg N/ha)",
        ),
    ]

    # Side-by-side treatment maps:
    # one comparative figure for each outcome within each study/year/variety.
    for (study, year, variety), g in stage.groupby(
        ["study", "year", "variety"],
        dropna=False,
    ):
        boundary = boundary_lookup[
            (study, year, variety)
        ]

        for metric, label in map_metrics:
            if metric not in g.columns:
                continue

            if num(g[metric]).notna().sum() == 0:
                continue

            filename = (
                f"{clean_filename(year)}__"
                f"{clean_filename(study)}__"
                f"{clean_filename(variety)}__"
                f"side_by_side__"
                f"{clean_filename(metric)}.png"
            )

            save_side_by_side_treatment_maps(
                g,
                metric,
                label,
                boundary,
                MAP_DIR / filename,
                manifest,
            )

    distribution_metrics = [
        (
            "mean_yield_kg_ha",
            "Yield (kg/ha)",
        ),
        (
            "yield_response_to_N_kg_ha",
            "Yield response to N (kg/ha)",
        ),
        (
            "AE_N_kg_grain_per_kg_N",
            "Agronomic efficiency of N, AE-N (kg grain/kg N)",
        ),
        (
            "PFP_N_kg_grain_per_kg_N",
            "Partial factor productivity of N, PFP-N (kg grain/kg N)",
        ),
        (
            "relative_yield_to_government_reference_pct",
            "Relative yield to N120-P-K reference (%)",
        ),
        (
            "potential_mineral_N_reduction_kg_ha",
            "Potential mineral-N reduction (kg N/ha)",
        ),
    ]

    for (study, year, variety), g in stage.groupby(
        ["study", "year", "variety"],
        dropna=False,
    ):
        for metric, label in distribution_metrics:
            if metric not in g.columns:
                continue

            if num(g[metric]).notna().sum() == 0:
                continue

            filename = (
                f"{clean_filename(year)}__"
                f"{clean_filename(study)}__"
                f"{clean_filename(variety)}__"
                f"side_by_side_distribution__"
                f"{clean_filename(metric)}.png"
            )

            save_side_by_side_treatment_distribution(
                g,
                metric,
                label,
                FIG_DIR / filename,
                manifest,
            )

    if TARGET_FILE.exists():
        target = pd.read_csv(TARGET_FILE)

        save_stage5_maps(
            target,
            coordinate_lookup,
            boundary_lookup,
            manifest,
        )

    manifest_df = pd.DataFrame(manifest)

    if boundary_metadata:
        boundary_df = pd.DataFrame(
            boundary_metadata
        )

        manifest_df = manifest_df.merge(
            boundary_df,
            on=["study", "year", "variety"],
            how="left",
        )

    manifest_df.to_csv(
        MANIFEST,
        index=False,
    )

    sites_with_coordinates = stage.loc[
        valid_latlon(
            num(stage["latitude"]),
            num(stage["longitude"]),
        ),
        "site",
    ].nunique()

    print("\n" + "=" * 108)
    print(
        "NSAF STAGE 1-6 MAPS AND INDIVIDUAL-SITE "
        "AGRONOMIC DISTRIBUTIONS"
    )
    print("=" * 108)

    print(f"Stage rows:             {len(stage):,}")
    print(f"Unique sites:           {stage['site'].nunique()}")
    print(f"Sites with coordinates: {sites_with_coordinates}")
    print(f"Ward boundary:          {BOUNDARY_FILE}")
    print("CRS:                    EPSG:4326 (degrees)")
    print("Map clipping:           study districts only")

    print("\nStudy boundary subsets:")

    for item in boundary_metadata:
        print(
            f"  {item['year']} | "
            f"{item['study']} | "
            f"{item['variety']} -> "
            f"{item['districts']} "
            f"[field={item['boundary_district_field']}; "
            f"wards={item['n_ward_polygons']}]"
        )

    print(f"\nMaps:                    {MAP_DIR}")
    print(f"Distribution figures:    {FIG_DIR}")
    print(f"Manifest:                {MANIFEST}")
    print(f"Figures/maps recorded:    {len(manifest)}")

    print("\nAll maps show measured trial sites only.")
    print("No DSM interpolation/extrapolation is applied.")


if __name__ == "__main__":
    main()
