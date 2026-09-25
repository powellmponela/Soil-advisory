from pathlib import Path
import json
import pandas as pd

try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError as exc:
    raise ImportError(
        "Install geopandas and shapely before running this publication step."
    ) from exc

ROOT = Path(r"D:\dss\SOIL ADVISORY")
INPUT = ROOT / "outputs" / "spatial_extrapolation" / "western_ae_gains_map_table.csv"
PUBLIC = ROOT / "frontend" / "public"

OUT_CSV = PUBLIC / "advisory_pixels.csv"
OUT_GEOJSON = PUBLIC / "advisory_pixels.geojson"
OUT_META = PUBLIC / "advisory_metadata.json"

PUBLIC_COLUMNS = [
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
    "predicted_PFP_N_kg_grain_per_kg_N",
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

def _as_bool(series):
    if series.dtype == bool:
        return series
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input not found:\n{INPUT}\n"
            "Run the spatial workflow first."
        )

    PUBLIC.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT)

    required = {
        "lat",
        "lon",
        "strategy",
        "target_yield_t_ha",
        "environmental_support",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    df = df.loc[_as_bool(df["environmental_support"])].copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(
        subset=["lat", "lon", "strategy", "target_yield_t_ha"]
    )

    keep = [c for c in PUBLIC_COLUMNS if c in df.columns]
    public = df[keep].copy()

    sort_cols = [
        c for c in [
            "province",
            "district",
            "palika",
            "target_yield_t_ha",
            "strategy",
            "lat",
            "lon",
        ]
        if c in public.columns
    ]
    public = public.sort_values(sort_cols).reset_index(drop=True)

    public.insert(
        0,
        "pixel_id",
        [f"px_{i:07d}" for i in range(1, len(public) + 1)],
    )

    public.to_csv(OUT_CSV, index=False)

    geometry = [
        Point(lon, lat)
        for lon, lat in zip(public["lon"], public["lat"])
    ]
    gdf = gpd.GeoDataFrame(
        public.copy(),
        geometry=geometry,
        crs="EPSG:4326",
    )
    gdf.to_file(OUT_GEOJSON, driver="GeoJSON")

    metadata = {
        "title": "Nepal Soil and Nutrient Advisory",
        "product": "Modelled pixel-level fertilizer target-setting advisory",
        "source_table": str(INPUT.relative_to(ROOT)),
        "public_csv": str(OUT_CSV.relative_to(ROOT)),
        "public_geojson": str(OUT_GEOJSON.relative_to(ROOT)),
        "n_records": int(len(public)),
        "strategies": sorted(
            public["strategy"].dropna().astype(str).unique().tolist()
        ),
        "target_yields_t_ha": sorted(
            pd.to_numeric(
                public["target_yield_t_ha"],
                errors="coerce",
            )
            .dropna()
            .unique()
            .tolist()
        ),
        "interpretation": (
            "Pixel values are modelled spatial response, nutrient-demand, "
            "and target-setting estimates. They are not direct soil "
            "measurements or field-specific fertilizer prescriptions."
        ),
        "support_rule": (
            "Only records with environmental_support == True "
            "are included in the public product."
        ),
    }

    OUT_META.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("Published web GIS products:")
    print(OUT_CSV)
    print(OUT_GEOJSON)
    print(OUT_META)
    print(f"Records published: {len(public)}")

if __name__ == "__main__":
    main()
