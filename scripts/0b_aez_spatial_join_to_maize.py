"""
0b_aez_spatial_join_to_maize.py

Simple Stage 0b AEZ assignment.

This script does exactly this:
1. Load maize.csv.
2. Load ecological-zone polygon shapefile.
3. Convert maize latitude/longitude to a point spatial layer.
4. Match point CRS to polygon CRS.
5. Spatially join points to polygons.
6. Extract polygon attributes for each point.
7. Save the attributes back into a working maize.csv.

Input maize.csv:
    Prefer:
    <project-root>/outputs/00_harmonized_trial_data/04_inputs_for_next_stage/maize.csv

    Fallback:
    <project-root>/Data/m_n_publications/maize.csv

AEZ polygon:
    <project-root>/Data/ecological zones/Cross_sections_of_Nepal_s_physiographic_regions.shp

Output maize.csv:
    <project-root>/outputs/00_harmonized_trial_data/00_data/maize.csv
    <project-root>/outputs/00_harmonized_trial_data/04_inputs_for_next_stage/maize.csv

Target AEZ classes:
    Terai
    Churia/Siwalik
    Mid-hills
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from _project_paths import DATA_DIR, OUTPUT_ROOT

try:
    import geopandas as gpd
except ImportError as exc:
    raise ImportError(
        "geopandas is required. Install it first, for example:\n"
        "python -m pip install geopandas"
    ) from exc


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

RAW_MAIZE_CSV = DATA_DIR / "m_n_publications" / "maize.csv"
STAGE0_DIR = OUTPUT_ROOT / "00_harmonized_trial_data"
STAGE0_DATA_DIR = STAGE0_DIR / "00_data"
STAGE0_TABLE_DIR = STAGE0_DIR / "01_descriptive_tables"
STAGE0_REPORT_DIR = STAGE0_DIR / "03_stage_report"
STAGE0_NEXT_DIR = STAGE0_DIR / "04_inputs_for_next_stage"

WORKING_MAIZE_CSV = STAGE0_NEXT_DIR / "maize.csv"

AEZ_SHP = (
    DATA_DIR
    / "ecological zones"
    / "Cross_sections_of_Nepal_s_physiographic_regions.shp"
)

OUT_MAIZE_CSV = STAGE0_DATA_DIR / "maize.csv"
OUT_NEXT_MAIZE_CSV = STAGE0_NEXT_DIR / "maize.csv"

TARGET_AE_ZONES = {"Terai", "Churia/Siwalik", "Mid-hills"}

LATITUDE_CANDIDATES = [
    "latitude",
    "lat",
    "Latitude",
    "LAT",
    "y",
    "Y",
]
LONGITUDE_CANDIDATES = [
    "longitude",
    "lon",
    "long",
    "Longitude",
    "LON",
    "LONG",
    "x",
    "X",
]

AEZ_ATTRIBUTE_CANDIDATES = [
    "AEZ",
    "AE_ZONE",
    "ae_zone",
    "zone",
    "Zone",
    "region",
    "Region",
    "REGION",
    "physio",
    "Physio",
    "PHYSIO",
    "physiographic",
    "Physiographic",
    "physiogra",
    "NAME",
    "Name",
    "name",
    "CLASS",
    "Class",
    "class",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def ensure_dirs() -> None:
    for d in [STAGE0_DATA_DIR, STAGE0_TABLE_DIR, STAGE0_REPORT_DIR, STAGE0_NEXT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def first_existing(candidates: Iterable[str], columns: Iterable[str]) -> str | None:
    column_set = set(columns)
    for c in candidates:
        if c in column_set:
            return c
    return None


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    txt = str(value).strip()
    if txt.lower() in {"nan", "none", "nat", "null"}:
        return ""
    return txt


def normalize_aez(value: object) -> str:
    txt = clean_text(value)
    low = txt.lower()

    if not low:
        return ""

    if "terai" in low or "tarai" in low:
        return "Terai"

    if "churia" in low or "chure" in low or "siwalik" in low or "shiwalik" in low:
        return "Churia/Siwalik"

    if (
        "mid hill" in low
        or "midhill" in low
        or "mid-hill" in low
        or "mid hills" in low
        or "midhills" in low
        or "middle mountain" in low
        or "middle mountains" in low
        or "mid mountain" in low
        or "mid mountains" in low
    ):
        return "Mid-hills"

    return "outside_target_ae_zone"


def choose_maize_input() -> Path:
    """Use the latest working maize.csv if it exists; otherwise raw publication maize.csv."""
    if WORKING_MAIZE_CSV.exists():
        return WORKING_MAIZE_CSV
    if RAW_MAIZE_CSV.exists():
        return RAW_MAIZE_CSV
    raise FileNotFoundError(
        "Could not find maize.csv.\n"
        f"Checked:\n- {WORKING_MAIZE_CSV}\n- {RAW_MAIZE_CSV}"
    )


def choose_aez_attribute(zones: gpd.GeoDataFrame) -> str:
    non_geom_cols = [c for c in zones.columns if c != "geometry"]
    if not non_geom_cols:
        raise ValueError("AEZ polygon file has no non-geometry attribute columns.")

    chosen = first_existing(AEZ_ATTRIBUTE_CANDIDATES, non_geom_cols)
    if chosen is not None:
        return chosen

    # Fallback: choose first non-geometry column.
    return non_geom_cols[0]


def safe_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove GeoPandas helper columns before CSV export."""
    drop_cols = [c for c in ["geometry", "index_right"] if c in df.columns]
    return pd.DataFrame(df.drop(columns=drop_cols, errors="ignore"))


# ---------------------------------------------------------------------
# Main spatial join
# ---------------------------------------------------------------------

def main() -> None:
    ensure_dirs()

    maize_path = choose_maize_input()

    if not AEZ_SHP.exists():
        raise FileNotFoundError(f"AEZ shapefile not found: {AEZ_SHP}")

    maize = pd.read_csv(maize_path, low_memory=False)

    lat_col = first_existing(LATITUDE_CANDIDATES, maize.columns)
    lon_col = first_existing(LONGITUDE_CANDIDATES, maize.columns)

    if lat_col is None or lon_col is None:
        raise ValueError(
            "Could not find latitude/longitude columns in maize.csv.\n"
            f"Latitude candidates: {LATITUDE_CANDIDATES}\n"
            f"Longitude candidates: {LONGITUDE_CANDIDATES}\n"
            f"Available columns: {list(maize.columns)}"
        )

    zones = gpd.read_file(AEZ_SHP)

    if zones.empty:
        raise ValueError(f"AEZ shapefile is empty: {AEZ_SHP}")

    if zones.crs is None:
        raise ValueError(
            f"AEZ shapefile has no CRS: {AEZ_SHP}\n"
            "Define the CRS before running this script."
        )

    aez_attr = choose_aez_attribute(zones)

    # Keep all polygon attributes, but prefix them to avoid collisions with maize columns.
    polygon_attrs = [c for c in zones.columns if c != "geometry"]
    zones_for_join = zones[polygon_attrs + ["geometry"]].copy()
    zones_for_join = zones_for_join.rename(
        columns={c: f"aez_poly_{c}" for c in polygon_attrs}
    )

    joined_attr = f"aez_poly_{aez_attr}"

    # Convert maize lat/lon to numeric and then to points in EPSG:4326.
    maize["longitude_for_ae"] = pd.to_numeric(maize[lon_col], errors="coerce")
    maize["latitude_for_ae"] = pd.to_numeric(maize[lat_col], errors="coerce")

    valid = maize["longitude_for_ae"].notna() & maize["latitude_for_ae"].notna()

    # Start with full maize dataframe so rows with missing coordinates are retained.
    out = maize.copy()

    # Initialize AEZ fields.
    out["coordinate_ae_zone_raw"] = ""
    out["coordinate_ae_zone"] = ""
    out["ae_zone_final"] = ""
    out["ae_zone_assignment_method"] = ""
    out["ae_zone_in_target_scope"] = False
    out["ae_zone_assignment_note"] = ""

    # Drop existing aez_poly columns if they exist from a previous run to avoid sjoin left/right suffixes
    overlap_cols = [c for c in zones_for_join.columns if c != "geometry" and c in out.columns]
    if overlap_cols:
        out = out.drop(columns=overlap_cols)
        maize = maize.drop(columns=overlap_cols)

    # Add empty polygon-attribute columns for all rows before assignment.
    for col in zones_for_join.columns:
        if col != "geometry":
            out[col] = ""

    if valid.any():
        points = gpd.GeoDataFrame(
            maize.loc[valid].copy(),
            geometry=gpd.points_from_xy(
                maize.loc[valid, "longitude_for_ae"],
                maize.loc[valid, "latitude_for_ae"],
            ),
            crs="EPSG:4326",
        )

        # Match CRS: reproject points to polygon CRS.
        points = points.to_crs(zones_for_join.crs)

        # Spatial join: extract polygon attributes for each point.
        joined = gpd.sjoin(
            points,
            zones_for_join,
            how="left",
            predicate="within",
        )

        # If any point lies exactly on a polygon boundary, try intersects.
        matched = joined[joined_attr].notna() if joined_attr in joined.columns else pd.Series(False, index=joined.index)
        unmatched_index = joined.index[~matched]

        if len(unmatched_index) > 0:
            retry_points = points.loc[unmatched_index].copy()
            retry = gpd.sjoin(
                retry_points,
                zones_for_join,
                how="left",
                predicate="intersects",
            )
            retry = retry[~retry.index.duplicated(keep="first")]

            for col in zones_for_join.columns:
                if col != "geometry" and col in retry.columns:
                    joined.loc[retry.index, col] = retry[col]

        joined = joined[~joined.index.duplicated(keep="first")]

        # Write polygon attributes back to the non-spatial maize dataframe.
        for col in zones_for_join.columns:
            if col != "geometry" and col in joined.columns:
                out.loc[joined.index, col] = joined[col].map(clean_text)

        print("DEBUG: joined_attr =", joined_attr)
        print("DEBUG: joined columns =", joined.columns.tolist())
        out.loc[joined.index, "coordinate_ae_zone_raw"] = joined[joined_attr].map(clean_text)
        out.loc[joined.index, "coordinate_ae_zone"] = joined[joined_attr].map(normalize_aez)

    has_target = out["coordinate_ae_zone"].isin(TARGET_AE_ZONES)
    has_polygon_match = out["coordinate_ae_zone_raw"].map(clean_text) != ""

    out.loc[has_target, "ae_zone_final"] = out.loc[has_target, "coordinate_ae_zone"]
    out.loc[has_target, "ae_zone_assignment_method"] = "coordinate_polygon_attribute"

    out.loc[has_polygon_match & ~has_target, "ae_zone_final"] = ""
    out.loc[has_polygon_match & ~has_target, "ae_zone_assignment_method"] = "polygon_outside_target_scope"

    out.loc[~has_polygon_match & valid, "ae_zone_final"] = ""
    out.loc[~has_polygon_match & valid, "ae_zone_assignment_method"] = "no_polygon_match"

    out.loc[~valid, "ae_zone_final"] = ""
    out.loc[~valid, "ae_zone_assignment_method"] = "missing_coordinates"

    out["ae_zone_in_target_scope"] = out["ae_zone_final"].isin(TARGET_AE_ZONES)

    out.loc[has_target, "ae_zone_assignment_note"] = (
        "AEZ assigned from ecological-zone polygon attribute using point-in-polygon join."
    )
    out.loc[has_polygon_match & ~has_target, "ae_zone_assignment_note"] = (
        "Point intersects ecological-zone polygon, but polygon attribute is outside target classes."
    )
    out.loc[~has_polygon_match & valid, "ae_zone_assignment_note"] = (
        "Valid coordinates available, but point did not intersect an ecological-zone polygon."
    )
    out.loc[~valid, "ae_zone_assignment_note"] = (
        "Latitude or longitude missing/non-numeric; no spatial AEZ assignment."
    )

    out = safe_output_columns(out)

    # Save maize.csv again with AEZ polygon attributes.
    out.to_csv(OUT_MAIZE_CSV, index=False)
    shutil.copy2(OUT_MAIZE_CSV, OUT_NEXT_MAIZE_CSV)

    # QA tables.
    summary = pd.DataFrame(
        [
            {"metric": "input_maize_csv", "value": str(maize_path)},
            {"metric": "aez_shapefile", "value": str(AEZ_SHP)},
            {"metric": "aez_polygon_attribute_used", "value": aez_attr},
            {"metric": "maize_rows", "value": len(out)},
            {"metric": "rows_with_valid_coordinates", "value": int(valid.sum())},
            {"metric": "rows_with_polygon_match", "value": int(has_polygon_match.sum())},
            {"metric": "rows_in_target_aez_scope", "value": int(out["ae_zone_in_target_scope"].sum())},
            {"metric": "output_maize_csv", "value": str(OUT_MAIZE_CSV)},
            {"metric": "next_stage_maize_csv", "value": str(OUT_NEXT_MAIZE_CSV)},
        ]
    )
    summary_path = STAGE0_TABLE_DIR / "stage0_aez_spatial_join_summary.csv"
    summary.to_csv(summary_path, index=False)

    counts = (
        out.groupby(["ae_zone_assignment_method", "ae_zone_final"], dropna=False)
        .size()
        .reset_index(name="n_rows")
        .sort_values(["ae_zone_assignment_method", "ae_zone_final"])
    )
    counts_path = STAGE0_TABLE_DIR / "stage0_aez_spatial_join_counts.csv"
    counts.to_csv(counts_path, index=False)

    review_cols = [
        "latitude_for_ae",
        "longitude_for_ae",
        "coordinate_ae_zone_raw",
        "coordinate_ae_zone",
        "ae_zone_final",
        "ae_zone_assignment_method",
        "ae_zone_in_target_scope",
        "ae_zone_assignment_note",
    ]
    review_cols = [c for c in review_cols if c in out.columns]
    review = out.loc[~out["ae_zone_in_target_scope"], review_cols].copy()
    review_path = STAGE0_TABLE_DIR / "stage0_aez_spatial_join_review_rows.csv"
    review.to_csv(review_path, index=False)

    report_path = STAGE0_REPORT_DIR / "stage0_aez_spatial_join_report.md"
    report_path.write_text(
        f"""# Stage 0b AEZ spatial join report

Input maize CSV: `{maize_path}`

AEZ shapefile: `{AEZ_SHP}`

Polygon attribute used for AEZ: `{aez_attr}`

Output maize CSV: `{OUT_MAIZE_CSV}`

Next-stage maize CSV: `{OUT_NEXT_MAIZE_CSV}`

Rows: {len(out)}

Rows with valid coordinates: {int(valid.sum())}

Rows with polygon match: {int(has_polygon_match.sum())}

Rows in target AEZ scope: {int(out["ae_zone_in_target_scope"].sum())}

Target AEZ classes:

- Terai
- Churia/Siwalik
- Mid-hills

This script converts maize latitude/longitude to points, reprojects points to the polygon CRS, extracts polygon attributes by spatial join, and saves the extracted AEZ attributes back into `maize.csv`.
""",
        encoding="utf-8",
    )

    print("Stage 0b AEZ spatial join complete.")
    print(f"Input maize CSV: {maize_path}")
    print(f"AEZ shapefile: {AEZ_SHP}")
    print(f"AEZ polygon attribute used: {aez_attr}")
    print(f"Output maize CSV: {OUT_MAIZE_CSV}")
    print(f"Next-stage maize CSV: {OUT_NEXT_MAIZE_CSV}")
    print(f"Summary: {summary_path}")
    print(f"Counts: {counts_path}")
    print(f"Review rows: {review_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
