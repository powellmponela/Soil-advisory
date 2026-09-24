#!/usr/bin/env python
"""
09_nsaf_baseline_maps.py

Stage 9A: NSAF baseline maps from the observed N0-P0-K0 control.

Design principle
----------------
- Use NSAF observations only for the baseline estimate.
- Do NOT use DSM values in this script.
- The baseline is extracted from the contrast:
      comparison == "Add P and K without N"
  where the benchmark treatment is Control (N0-P0-K0).
- The analytical spatial unit is trial_year_id.
- This script maps observed trial-site baseline yield. It does NOT interpolate.
  Spatial extrapolation is a later step after examining data distribution.

Outputs
-------
1. baseline_trial_year.csv
2. baseline_trial_year.gpkg
3. baseline_summary_district_year.csv
4. baseline_yield_all_nsaf.png
5. baseline_yield_<district>.png
6. baseline_yield_<district>_<year>.png

Optional district boundaries may be supplied for map context only.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASELINE_COMPARISON = "Add P and K without N"
BASELINE_TREATMENT = "Control"
WGS84 = "EPSG:4326"


def slugify(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def read_baseline(xlsx: Path) -> pd.DataFrame:
    contrasts = pd.read_excel(
        xlsx,
        sheet_name="Response_Contrast_Table",
        engine="openpyxl",
    )

    required = {
        "trial_year_id",
        "trial_id",
        "year",
        "district",
        "site",
        "latitude",
        "longitude",
        "comparison",
        "benchmark_treatment",
        "benchmark_N_kg_ha",
        "benchmark_yield_t_ha",
        "spatial_eligible",
    }
    missing = sorted(required - set(contrasts.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    comparison = contrasts["comparison"].astype(str).str.strip()
    treatment = contrasts["benchmark_treatment"].astype(str).str.strip()
    n_rate = pd.to_numeric(contrasts["benchmark_N_kg_ha"], errors="coerce")

    eligible = contrasts["spatial_eligible"]
    if eligible.dtype != bool:
        eligible = eligible.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})

    keep = (
        comparison.eq(BASELINE_COMPARISON)
        & treatment.str.contains(BASELINE_TREATMENT, case=False, na=False)
        & n_rate.eq(0)
        & eligible
    )

    baseline = contrasts.loc[
        keep,
        [
            "trial_year_id",
            "trial_id",
            "year",
            "district",
            "site",
            "latitude",
            "longitude",
            "benchmark_treatment",
            "benchmark_N_kg_ha",
            "benchmark_yield_t_ha",
        ],
    ].copy()

    baseline = baseline.rename(
        columns={
            "benchmark_treatment": "baseline_treatment",
            "benchmark_N_kg_ha": "baseline_N_kg_ha",
            "benchmark_yield_t_ha": "baseline_yield_t_ha",
        }
    )

    baseline["year"] = pd.to_numeric(baseline["year"], errors="coerce").astype("Int64")
    baseline["latitude"] = pd.to_numeric(baseline["latitude"], errors="coerce")
    baseline["longitude"] = pd.to_numeric(baseline["longitude"], errors="coerce")
    baseline["baseline_yield_t_ha"] = pd.to_numeric(
        baseline["baseline_yield_t_ha"], errors="coerce"
    )

    baseline = baseline.dropna(
        subset=["trial_year_id", "year", "district", "latitude", "longitude", "baseline_yield_t_ha"]
    )

    # Baseline is N0-P0-K0. P and K rates are not separate benchmark columns in
    # Response_Contrast_Table, so record them explicitly as zero for downstream use.
    baseline["baseline_P2O5_kg_ha"] = 0.0
    baseline["baseline_K2O_kg_ha"] = 0.0
    baseline["baseline_N_kg_ha"] = 0.0
    baseline["baseline_code"] = "N0-P0-K0"

    # trial_year_id is the spatial analytical unit. If duplicate baseline rows occur,
    # they should be identical or near-identical. Collapse defensively to one record.
    dup_counts = baseline.groupby("trial_year_id", dropna=False).size()
    if (dup_counts > 1).any():
        check = (
            baseline.groupby("trial_year_id")
            .agg(
                n=("trial_year_id", "size"),
                yield_min=("baseline_yield_t_ha", "min"),
                yield_max=("baseline_yield_t_ha", "max"),
                lat_min=("latitude", "min"),
                lat_max=("latitude", "max"),
                lon_min=("longitude", "min"),
                lon_max=("longitude", "max"),
            )
        )
        bad = check[
            (check["yield_max"] - check["yield_min"] > 1e-8)
            | (check["lat_max"] - check["lat_min"] > 1e-6)
            | (check["lon_max"] - check["lon_min"] > 1e-6)
        ]
        if not bad.empty:
            raise ValueError(
                "Conflicting duplicate baseline records found for trial_year_id: "
                + ", ".join(map(str, bad.index[:10]))
            )
        baseline = baseline.drop_duplicates("trial_year_id", keep="first")

    baseline = baseline.sort_values(["district", "year", "site", "trial_year_id"]).reset_index(drop=True)

    if baseline.empty:
        raise ValueError(
            "No baseline rows found. Check the comparison/treatment labels in Response_Contrast_Table."
        )

    return baseline


def read_district_boundaries(path: Path | None, name_field: str | None) -> gpd.GeoDataFrame | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"District boundary file not found: {path}")

    boundaries = gpd.read_file(path)
    if boundaries.empty:
        raise ValueError(f"District boundary file is empty: {path}")

    if boundaries.crs is None:
        raise ValueError("District boundary layer has no CRS.")
    boundaries = boundaries.to_crs(WGS84)

    if name_field:
        if name_field not in boundaries.columns:
            raise ValueError(
                f"Boundary name field '{name_field}' not found. Available columns: {list(boundaries.columns)}"
            )
        field = name_field
    else:
        candidates = [
            "district", "DISTRICT", "District", "DIST_NAME", "DISTRICT_N", "NAME_2", "ADM2_EN", "name"
        ]
        field = next((c for c in candidates if c in boundaries.columns), None)
        if field is None:
            raise ValueError(
                "Could not infer district-name column. Use --district-name-field. "
                f"Available columns: {list(boundaries.columns)}"
            )

    boundaries = boundaries[[field, "geometry"]].rename(columns={field: "district_boundary_name"})
    boundaries["district_key"] = boundaries["district_boundary_name"].astype(str).str.strip().str.lower()
    return boundaries


def district_boundary_subset(
    boundaries: gpd.GeoDataFrame | None,
    districts: list[str],
) -> gpd.GeoDataFrame | None:
    if boundaries is None:
        return None
    wanted = {str(d).strip().lower() for d in districts}
    out = boundaries[boundaries["district_key"].isin(wanted)].copy()
    return out if not out.empty else None


def make_geodataframe(baseline: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        baseline.copy(),
        geometry=gpd.points_from_xy(baseline["longitude"], baseline["latitude"]),
        crs=WGS84,
    )


def add_padding(ax, xs: pd.Series, ys: pd.Series, frac: float = 0.08) -> None:
    xmin, xmax = float(xs.min()), float(xs.max())
    ymin, ymax = float(ys.min()), float(ys.max())
    dx = max(xmax - xmin, 0.02)
    dy = max(ymax - ymin, 0.02)
    ax.set_xlim(xmin - dx * frac, xmax + dx * frac)
    ax.set_ylim(ymin - dy * frac, ymax + dy * frac)


def plot_baseline(
    points: gpd.GeoDataFrame,
    out_png: Path,
    title: str,
    boundaries: gpd.GeoDataFrame | None,
    vmin: float,
    vmax: float,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 7.5))

    if boundaries is not None and not boundaries.empty:
        boundaries.boundary.plot(ax=ax, linewidth=1.0)

    points.plot(
        ax=ax,
        column="baseline_yield_t_ha",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
        markersize=48,
        edgecolor="black",
        linewidth=0.35,
        legend=True,
        legend_kwds={"label": "Observed control yield (t ha$^{-1}$)", "shrink": 0.75},
    )

    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, linewidth=0.25, alpha=0.35)

    if boundaries is None or boundaries.empty:
        add_padding(ax, points["longitude"], points["latitude"])

    ax.text(
        0.01,
        0.01,
        "NSAF observed baseline: N0-P0-K0 control; no DSM extrapolation",
        transform=ax.transAxes,
        fontsize=8.5,
        va="bottom",
        ha="left",
    )

    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def summarise(baseline: pd.DataFrame) -> pd.DataFrame:
    return (
        baseline.groupby(["district", "year"], dropna=False)
        .agg(
            n_trial_years=("trial_year_id", "nunique"),
            n_sites=("site", "nunique"),
            mean_baseline_yield_t_ha=("baseline_yield_t_ha", "mean"),
            median_baseline_yield_t_ha=("baseline_yield_t_ha", "median"),
            sd_baseline_yield_t_ha=("baseline_yield_t_ha", "std"),
            min_baseline_yield_t_ha=("baseline_yield_t_ha", "min"),
            max_baseline_yield_t_ha=("baseline_yield_t_ha", "max"),
            min_latitude=("latitude", "min"),
            max_latitude=("latitude", "max"),
            min_longitude=("longitude", "min"),
            max_longitude=("longitude", "max"),
        )
        .reset_index()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create NSAF observed baseline-yield maps.")
    parser.add_argument(
        "--xlsx",
        required=True,
        type=Path,
        help="Path to NSAF_spatial_trial_and_response_contrast_datasets.xlsx",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/stage09_baseline"),
        help="Output directory",
    )
    parser.add_argument(
        "--districts",
        type=Path,
        default=None,
        help="Optional district boundary layer (gpkg/shp/geojson) for map context only",
    )
    parser.add_argument(
        "--district-name-field",
        default=None,
        help="Optional district-name field in the boundary layer",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    baseline = read_baseline(args.xlsx)
    gdf = make_geodataframe(baseline)
    boundaries = read_district_boundaries(args.districts, args.district_name_field)

    # Common colour scale across every output map so maps are directly comparable.
    vmin = float(baseline["baseline_yield_t_ha"].min())
    vmax = float(baseline["baseline_yield_t_ha"].max())
    if np.isclose(vmin, vmax):
        vmax = vmin + 1e-6

    baseline.drop(columns=[], errors="ignore").to_csv(
        args.out / "baseline_trial_year.csv", index=False
    )
    gdf.to_file(args.out / "baseline_trial_year.gpkg", layer="baseline_trial_year", driver="GPKG")
    summarise(baseline).to_csv(args.out / "baseline_summary_district_year.csv", index=False)

    all_boundaries = district_boundary_subset(boundaries, sorted(baseline["district"].unique()))
    plot_baseline(
        gdf,
        args.out / "baseline_yield_all_nsaf.png",
        "NSAF observed baseline yield: N0-P0-K0",
        all_boundaries,
        vmin,
        vmax,
    )

    for district, district_df in gdf.groupby("district", sort=True):
        district_name = str(district)
        district_boundaries = district_boundary_subset(boundaries, [district_name])

        plot_baseline(
            district_df,
            args.out / f"baseline_yield_{slugify(district_name)}.png",
            f"{district_name}: observed NSAF baseline yield (N0-P0-K0)",
            district_boundaries,
            vmin,
            vmax,
        )

        for year, year_df in district_df.groupby("year", sort=True):
            plot_baseline(
                year_df,
                args.out / f"baseline_yield_{slugify(district_name)}_{int(year)}.png",
                f"{district_name}, {int(year)}: observed NSAF baseline yield (N0-P0-K0)",
                district_boundaries,
                vmin,
                vmax,
            )

    print("Baseline mapping complete")
    print(f"Trial-year baseline records: {len(baseline)}")
    print(f"Districts: {', '.join(sorted(map(str, baseline['district'].unique())))}")
    print(f"Years: {', '.join(map(str, sorted(baseline['year'].dropna().astype(int).unique())))}")
    print(f"Outputs: {args.out.resolve()}")


if __name__ == "__main__":
    main()
