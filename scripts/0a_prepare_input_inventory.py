"""
0a_prepare_input_inventory.py

Stage 0 starter script for the Soil Advisory workflow.

Purpose
-------
Create a transparent inventory of the static project inputs before any modelling:
- m_n_publications maize database and crosswalks
- local downloaded DSM soil layers at native/original resolution
- ecological-zone boundary used to clip/crop DSM to Terai, Churia/Siwalik and Mid-hills
- administrative boundaries for ward/municipality/district/province overlays
- optional literature folder

This script DOES NOT:
- call the NARC DSM API
- modify, move, or delete source files
- extract PDFs
- resample DSM rasters
- impute soil or treatment values

Main outputs
------------
outputs/00_harmonized_trial_data/00_data/stage0_input_inventory.csv
outputs/00_harmonized_trial_data/01_descriptive_tables/stage0_dsm_layer_inventory.csv
outputs/00_harmonized_trial_data/01_descriptive_tables/stage0_m_n_publications_quick_summary.csv
outputs/00_harmonized_trial_data/03_stage_report/stage0_input_inventory_report.md
outputs/00_harmonized_trial_data/04_inputs_for_next_stage/stage0_input_inventory.csv
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

try:
    from _project_paths import (
        BASE_DIR,
        DATA_DIR,
        OUTPUT_ROOT,
        M_N_PUBLICATIONS_DIR,
        DSM_DIR,
        ECOLOGICAL_ZONES_DIR,
        ECOLOGICAL_ZONES_SHP,
        BOUNDARY_DIR,
        ensure_all_output_dirs,
        ensure_stage_dirs,
    )
    from _stage_qa import write_basic_stage_qa, write_input_output_audit
except ImportError:
    # Fallback so this script can run by itself during debugging.
    BASE_DIR = Path(os.environ.get("SOIL_ADVISORY_ROOT", Path(__file__).resolve().parents[1]))
    DATA_DIR = BASE_DIR / "Data"
    OUTPUT_ROOT = BASE_DIR / "outputs"
    M_N_PUBLICATIONS_DIR = DATA_DIR / "m_n_publications"
    DSM_DIR = DATA_DIR / "dsm"
    ECOLOGICAL_ZONES_DIR = DATA_DIR / "ecological zones"
    ECOLOGICAL_ZONES_SHP = ECOLOGICAL_ZONES_DIR / "Cross_sections_of_Nepal_s_physiographic_regions.shp"
    BOUNDARY_DIR = DATA_DIR / "boundary"

    def ensure_stage_dirs(stage_no: int) -> dict[str, Path]:
        stage_dir = OUTPUT_ROOT / "00_harmonized_trial_data"
        subdirs = {
            "00_data": stage_dir / "00_data",
            "01_descriptive_tables": stage_dir / "01_descriptive_tables",
            "02_plots": stage_dir / "02_plots",
            "03_stage_report": stage_dir / "03_stage_report",
            "04_inputs_for_next_stage": stage_dir / "04_inputs_for_next_stage",
        }
        for directory in subdirs.values():
            directory.mkdir(parents=True, exist_ok=True)
        return subdirs

    def ensure_all_output_dirs() -> None:
        ensure_stage_dirs(0)

    def write_basic_stage_qa(*args, **kwargs) -> None:  # type: ignore[no-redef]
        return None

    def write_input_output_audit(*args, **kwargs) -> None:  # type: ignore[no-redef]
        return None


STAGE_NO = 0
SCRIPT_NAME = Path(__file__).name

EXPECTED_M_N_PUBLICATION_FILES = [
    "maize.csv",
    "maize.xlsx",
    "maize_treatment_crosswalk.csv",
    "maize_unit_crosswalk.csv",
    "maize_variable_dictionary.csv",
    "maize_qa.csv",
    "maize_data_refresh_summary.csv",
]

EXPECTED_DSM_LAYER_FOLDERS = [
    "boron",
    "clay",
    "nitrogen",
    "organic",
    "parentsoil",
    "ph",
    "phosphorus",
    "potassium",
    "sand",
    "silt",
    "zinc",
]

EXPECTED_BOUNDARY_INPUTS = [
    "ward_level_boundary.gpkg",
    "wards.shp",
    "province_district_municipality/local_unit.shp",
    "known_sites/nepal_research_sites.csv",
]

RASTER_EXTENSIONS = {".tif", ".tiff", ".vrt", ".img"}
VECTOR_EXTENSIONS = {".shp", ".gpkg", ".geojson"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".xls", ".dbf"}


def file_size_mb(path: Path) -> float | None:
    if not path.exists() or not path.is_file():
        return None
    return round(path.stat().st_size / (1024 * 1024), 4)


def count_files(path: Path) -> int:
    if path.is_file():
        return 1
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def list_extensions(path: Path) -> str:
    if path.is_file():
        return path.suffix.lower()
    if not path.exists() or not path.is_dir():
        return ""
    extensions = sorted({item.suffix.lower() for item in path.rglob("*") if item.is_file() and item.suffix})
    return ";".join(extensions)


def path_status(path: Path, category: str, expected: bool = True, notes: str = "") -> dict:
    return {
        "category": category,
        "path": str(path),
        "name": path.name,
        "expected": expected,
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size_mb": file_size_mb(path),
        "n_files_recursive": count_files(path),
        "extensions_detected": list_extensions(path),
        "notes": notes,
    }


def build_input_inventory() -> pd.DataFrame:
    rows: list[dict] = []

    rows.extend(
        [
            path_status(BASE_DIR, "project_root", True, "Main project folder."),
            path_status(DATA_DIR, "data_root", True, "Main data folder."),
            path_status(OUTPUT_ROOT, "outputs_root", True, "Main output folder."),
            path_status(M_N_PUBLICATIONS_DIR, "m_n_publications_dir", True, "Harmonized Nepal maize publication data."),
            path_status(DSM_DIR, "local_dsm_dir", True, "Static local DSM files. Do not call DSM API."),
            path_status(ECOLOGICAL_ZONES_DIR, "ecological_zones_dir", True, "Terai, Churia/Siwalik and Mid-hill clipping boundary."),
            path_status(ECOLOGICAL_ZONES_SHP, "ecological_zones_shapefile", True, "Physiographic-region shapefile."),
            path_status(BOUNDARY_DIR, "boundary_dir", True, "Ward/municipality/district/province boundaries."),
            path_status(BASE_DIR / "Literature", "literature_dir", False, "Optional publication PDFs/text files."),
        ]
    )

    for filename in EXPECTED_M_N_PUBLICATION_FILES:
        rows.append(
            path_status(
                M_N_PUBLICATIONS_DIR / filename,
                "m_n_publications_file",
                True,
                "Expected m_n_publications input.",
            )
        )

    for folder in EXPECTED_DSM_LAYER_FOLDERS:
        rows.append(
            path_status(
                DSM_DIR / folder,
                "dsm_layer_folder",
                True,
                "Expected static local DSM layer folder at native/original resolution.",
            )
        )

    for rel_path in EXPECTED_BOUNDARY_INPUTS:
        rows.append(
            path_status(
                BOUNDARY_DIR / rel_path,
                "boundary_input",
                True,
                "Boundary input for overlay or aggregation.",
            )
        )

    return pd.DataFrame(rows)


def build_dsm_layer_inventory() -> pd.DataFrame:
    rows: list[dict] = []
    for folder in EXPECTED_DSM_LAYER_FOLDERS:
        layer_dir = DSM_DIR / folder
        files = []
        if layer_dir.exists():
            files = [item for item in layer_dir.rglob("*") if item.is_file()]

        raster_files = [p for p in files if p.suffix.lower() in RASTER_EXTENSIONS]
        vector_files = [p for p in files if p.suffix.lower() in VECTOR_EXTENSIONS]
        table_files = [p for p in files if p.suffix.lower() in TABLE_EXTENSIONS]

        rows.append(
            {
                "dsm_layer": folder,
                "folder": str(layer_dir),
                "folder_exists": layer_dir.exists(),
                "n_files": len(files),
                "n_raster_files": len(raster_files),
                "n_vector_files": len(vector_files),
                "n_table_files": len(table_files),
                "primary_raster_file": str(raster_files[0]) if raster_files else "",
                "primary_vector_file": str(vector_files[0]) if vector_files else "",
                "extensions_detected": ";".join(sorted({p.suffix.lower() for p in files if p.suffix})),
                "soil_role": soil_role(folder),
            }
        )
    return pd.DataFrame(rows)


def soil_role(layer_name: str) -> str:
    mapping = {
        "ph": "soil reaction / acidity",
        "organic": "soil organic matter or carbon proxy",
        "nitrogen": "total nitrogen",
        "phosphorus": "available phosphorus",
        "potassium": "available/exchangeable potassium",
        "boron": "micronutrient",
        "zinc": "micronutrient",
        "sand": "texture fraction",
        "silt": "texture fraction",
        "clay": "texture fraction",
        "parentsoil": "parent soil / soil class vector",
    }
    return mapping.get(layer_name, "soil covariate")


def first_existing(columns: Iterable[str], df: pd.DataFrame) -> str | None:
    for col in columns:
        if col in df.columns:
            return col
    return None


def summarize_m_n_publications() -> pd.DataFrame:
    maize_csv = M_N_PUBLICATIONS_DIR / "maize.csv"
    if not maize_csv.exists():
        return pd.DataFrame(
            [
                {
                    "metric": "maize_csv_exists",
                    "value": False,
                    "notes": f"File not found: {maize_csv}",
                }
            ]
        )

    df = pd.read_csv(maize_csv, low_memory=False)
    rows: list[dict] = [
        {"metric": "maize_csv_exists", "value": True, "notes": str(maize_csv)},
        {"metric": "n_rows", "value": len(df), "notes": "Rows in m_n_publications maize.csv"},
        {"metric": "n_columns", "value": df.shape[1], "notes": "Columns in m_n_publications maize.csv"},
    ]

    quick_count_specs = {
        "source_id": ["source_id", "source_number", "study_id", "source"],
        "year": ["year", "trial_year", "year_start", "year_end"],
        "season": ["season", "maize_season"],
        "district": ["district"],
        "agroecology": ["agroecology", "agroecology_region", "region", "landform"],
        "treatment_group": ["treatment_group", "trial_family", "treatment_family", "treatment_code"],
    }

    for metric, candidate_cols in quick_count_specs.items():
        col = first_existing(candidate_cols, df)
        if col is None:
            rows.append({"metric": f"n_unique_{metric}", "value": None, "notes": "Column not available"})
            continue
        rows.append(
            {
                "metric": f"n_unique_{metric}",
                "value": int(df[col].nunique(dropna=True)),
                "notes": f"Column used: {col}",
            }
        )

    key_numeric = [
        "grain_yield_Mg_ha",
        "grain_yield_kg_ha",
        "N_rate_kg_ha",
        "N_fert_kg_ha",
        "P2O5_rate_kg_ha",
        "P2O5_fert_kg_ha",
        "K2O_rate_kg_ha",
        "K2O_fert_kg_ha",
    ]
    for col in key_numeric:
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        rows.extend(
            [
                {"metric": f"{col}_n_non_missing", "value": int(values.notna().sum()), "notes": ""},
                {"metric": f"{col}_median", "value": float(values.median()) if values.notna().any() else None, "notes": ""},
                {"metric": f"{col}_min", "value": float(values.min()) if values.notna().any() else None, "notes": ""},
                {"metric": f"{col}_max", "value": float(values.max()) if values.notna().any() else None, "notes": ""},
            ]
        )

    return pd.DataFrame(rows)


def write_top_counts(maize_csv: Path, tables_dir: Path) -> None:
    if not maize_csv.exists():
        return
    df = pd.read_csv(maize_csv, low_memory=False)
    count_specs = {
        "season": ["season", "maize_season"],
        "district": ["district"],
        "source_id": ["source_id", "source_number", "study_id", "source"],
        "treatment_group": ["treatment_group", "trial_family", "treatment_family", "treatment_code"],
        "agroecology": ["agroecology", "agroecology_region", "region", "landform"],
    }
    for label, candidates in count_specs.items():
        col = first_existing(candidates, df)
        if col is None:
            continue
        counts = (
            df[col]
            .astype("object")
            .where(df[col].notna(), "missing")
            .value_counts(dropna=False)
            .reset_index()
        )
        counts.columns = [col, "n_rows"]
        counts.to_csv(tables_dir / f"stage0_m_n_publications_counts_by_{label}.csv", index=False)


def write_report(
    dirs: dict[str, Path],
    inventory: pd.DataFrame,
    dsm_inventory: pd.DataFrame,
    mnpub_summary: pd.DataFrame,
) -> Path:
    report_path = dirs["03_stage_report"] / "stage0_input_inventory_report.md"
    missing_expected = inventory[(inventory["expected"]) & (~inventory["exists"])]
    found_dsm = dsm_inventory[dsm_inventory["folder_exists"]]

    text = f"""# Stage 0a input inventory report

Script: `{SCRIPT_NAME}`

Project root: `{BASE_DIR}`

## Purpose

This script checks that the static input files needed for Stage 0 are present before the workflow proceeds. It does not call the DSM API, does not move source files, and does not alter downloaded DSM resolution.

## Key checks

- Expected input records checked: {len(inventory)}
- Missing expected inputs: {len(missing_expected)}
- DSM layer folders found: {len(found_dsm)} of {len(dsm_inventory)}
- m_n_publications summary rows: {len(mnpub_summary)}

## Soil-data policy

1. Use soil values reported in `m_n_publications/maize.csv` first.
2. Fill missing soil covariates from locally downloaded high-resolution NARC DSM layers in `Data/dsm`.
3. Keep DSM rasters at native/original resolution.
4. Do not call the DSM API.
5. Use ISRIC/SoilGrids only for supplemental properties not provided locally, such as CEC, bulk density, soil depth/depth-to-bedrock proxy, and volumetric water content.

## Outputs

- `stage0_input_inventory.csv`
- `stage0_dsm_layer_inventory.csv`
- `stage0_m_n_publications_quick_summary.csv`
- `stage0_m_n_publications_counts_by_*.csv`

## Missing expected inputs

"""
    if len(missing_expected) == 0:
        text += "No expected inputs are missing.\n"
    else:
        for _, row in missing_expected.iterrows():
            text += f"- `{row['path']}` ({row['category']})\n"

    report_path.write_text(text, encoding="utf-8")
    return report_path


def main() -> None:
    ensure_all_output_dirs()
    dirs = ensure_stage_dirs(STAGE_NO)

    inventory = build_input_inventory()
    dsm_inventory = build_dsm_layer_inventory()
    mnpub_summary = summarize_m_n_publications()

    inventory_path = dirs["00_data"] / "stage0_input_inventory.csv"
    dsm_inventory_path = dirs["01_descriptive_tables"] / "stage0_dsm_layer_inventory.csv"
    mnpub_summary_path = dirs["01_descriptive_tables"] / "stage0_m_n_publications_quick_summary.csv"

    inventory.to_csv(inventory_path, index=False)
    dsm_inventory.to_csv(dsm_inventory_path, index=False)
    mnpub_summary.to_csv(mnpub_summary_path, index=False)

    # Also copy the inventory forward so later Stage 0 scripts can validate inputs.
    next_inventory_path = dirs["04_inputs_for_next_stage"] / inventory_path.name
    shutil.copy2(inventory_path, next_inventory_path)

    write_top_counts(M_N_PUBLICATIONS_DIR / "maize.csv", dirs["01_descriptive_tables"])

    report_path = write_report(dirs, inventory, dsm_inventory, mnpub_summary)

    # Stage QA: descriptive checks for the inventory tables themselves.
    write_basic_stage_qa(
        inventory,
        STAGE_NO,
        "stage0_input_inventory",
        group_cols=["category", "exists", "expected"],
        numeric_cols=["size_mb", "n_files_recursive"],
    )
    write_basic_stage_qa(
        dsm_inventory,
        STAGE_NO,
        "stage0_dsm_layer_inventory",
        group_cols=["dsm_layer", "folder_exists", "soil_role"],
        numeric_cols=["n_files", "n_raster_files", "n_vector_files", "n_table_files"],
    )

    write_input_output_audit(
        stage_no=STAGE_NO,
        script_name=SCRIPT_NAME,
        inputs=[BASE_DIR, DATA_DIR, M_N_PUBLICATIONS_DIR, DSM_DIR, ECOLOGICAL_ZONES_SHP, BOUNDARY_DIR],
        outputs=[inventory_path, dsm_inventory_path, mnpub_summary_path, next_inventory_path, report_path],
        notes="Stage 0a input inventory and static input policy check.",
    )

    print("Stage 0a input inventory complete.")
    print(f"Inventory: {inventory_path}")
    print(f"DSM inventory: {dsm_inventory_path}")
    print(f"Publication summary: {mnpub_summary_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
