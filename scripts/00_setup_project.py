"""
00_setup_project.py

Stage 00 project setup for the Soil Advisory workflow.

Purpose
-------
Creates and manages the project folder structure before any analytical script runs.
This script is intentionally safe and idempotent: by default it creates missing folders
and writes folder manifests, but it does not delete or overwrite input data.

Default project root:
    C:\\SOIL ADVISORY

Run:
    python 00_setup_project.py

Optional:
    python 00_setup_project.py --project-root "C:\\SOIL ADVISORY"
    python 00_setup_project.py --touch-gitkeep

Outputs
-------
    outputs/_project_folder_manifest.csv
    outputs/_stage_io_map.csv
    outputs/_project_config.json
    logs/00_setup_project.log
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StageSpec:
    stage_no: str
    folder: str
    label: str
    main_input: str
    main_output: str


STAGES: list[StageSpec] = [
    StageSpec(
        "00",
        "00_harmonized_trial_data",
        "Treatment-family harmonization and soil-data standardization",
        "m_n_publications, local DSM, ecological zones, boundary, NSAF/raw trial files",
        "Clean harmonized maize trial database with standardized soil covariates",
    ),
    StageSpec(
        "01",
        "01_trial_response_calibration",
        "Trial-response calibration",
        "Harmonized multi-year trial database from Stage 00",
        "Attainable yield, AE-N, treatment-response envelopes",
    ),
    StageSpec(
        "02",
        "02_farmer_yield_anchoring",
        "Farmer-yield anchoring",
        "Crop-cut and farmer-survey data",
        "Actual yield and current management baseline",
    ),
    StageSpec(
        "03",
        "03_yield_gap_target_yield",
        "Yield-gap and target-yield setting",
        "Trial attainable yield and farmer actual yield",
        "Low, medium, and high target-yield scenarios",
    ),
    StageSpec(
        "04",
        "04_response_domain_transfer",
        "Response-domain extrapolation",
        "DSM, climate, terrain, season, agroecology and trial/crop-cut locations",
        "Transferability classes and response-domain confidence",
    ),
    StageSpec(
        "05",
        "05_nsaf_innovation_targeting",
        "NSAF/Pandit summer-monsoon innovation targeting",
        "NSAF trial contrasts and response-domain confidence",
        "PCU, UDP, V6/V10 timing, FYM, Zn/S suitability and N-saving layers",
    ),
    StageSpec(
        "06",
        "06_fertilizer_demand_estimation",
        "Fertilizer-demand estimation",
        "Target yield, soil supply, AE-N, QUEFTS/nutrient-balance assumptions",
        "N demand and fertilizer-demand classes",
    ),
    StageSpec(
        "07",
        "07_spatial_advisory_ensemble",
        "Spatial advisory ensemble",
        "Trial response, crop-cut yield gap, response-domain, innovation and fertilizer-demand layers",
        "Advisory zones and response-confidence classes",
    ),
    StageSpec(
        "08",
        "08_admin_aggregation_country",
        "District-to-country aggregation",
        "Advisory-zone outputs, maize area, boundary layers and census/admin data",
        "Ward, municipality, district, province and national fertilizer-demand scenarios",
    ),
    StageSpec(
        "99",
        "99_reports_recommendation_package",
        "Reports and recommendation package",
        "Final stage outputs from Stages 00-08",
        "Maps, tables, stage reports and recommendation packages",
    ),
]


STAGE_SUBFOLDERS = [
    "00_data",
    "01_descriptive_tables",
    "02_plots",
    "03_stage_report",
    "04_inputs_for_next_stage",
]


DATA_SUBFOLDERS = [
    "m_n_publications",
    "dsm",
    "ecological zones",
    "boundary",
    "nsaf_trials",
    "crop_cut",
    "farmer_survey",
    "maize_area",
    "climate",
    "isric_soilgrids",
    "raw",
    "interim",
    "processed",
]


TOP_LEVEL_FOLDERS = [
    "Data",
    "scripts",
    "outputs",
    "logs",
    "temp",
    "docs",
    "maps",
    "reports",
]


def setup_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )


def make_dir(path: Path, created: list[dict[str, str]]) -> None:
    existed_before = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    created.append(
        {
            "path": str(path),
            "created_now": str(not existed_before),
            "exists_after": str(path.exists()),
        }
    )


def write_csv(path: Path, rows: Iterable[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def touch_gitkeep(folder: Path) -> None:
    gitkeep = folder / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("", encoding="utf-8")


def build_project_config(project_root: Path) -> dict[str, object]:
    data_dir = project_root / "Data"
    outputs_dir = project_root / "outputs"
    return {
        "project_root": str(project_root),
        "created_or_updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_dir": str(data_dir),
        "outputs_dir": str(outputs_dir),
        "logs_dir": str(project_root / "logs"),
        "scripts_dir": str(project_root / "scripts"),
        "soil_policy": {
            "publication_soil_priority": 1,
            "local_dsm_priority": 2,
            "isric_supplement_priority": 3,
            "use_dsm_api": False,
            "preserve_native_dsm_resolution": True,
            "local_dsm_folder": str(data_dir / "dsm"),
            "isric_supplement_folder": str(data_dir / "isric_soilgrids"),
            "notes": (
                "Use soil reported in publications first. Fill missing values from local downloaded DSM. "
                "Use ISRIC SoilGrids only for supplemental variables such as CEC, bulk density, "
                "soil depth/depth-to-bedrock proxy and volumetric water content. Do not call DSM API."
            ),
        },
        "spatial_frame": {
            "regions": ["Terai", "Churia/Siwalik", "Mid-hills"],
            "seasons": ["spring", "winter", "summer_monsoon"],
            "hubs": ["east_terai_hub", "west_terai_hub", "national_combined"],
            "administrative_units": ["ward", "municipality", "district", "province", "country"],
        },
        "stage_subfolders": STAGE_SUBFOLDERS,
    }


def inspect_required_inputs(project_root: Path) -> list[dict[str, object]]:
    data_dir = project_root / "Data"
    required = [
        ("m_n_publications", data_dir / "m_n_publications", "Required for Stage 00 multi-year maize trial evidence"),
        ("m_n_publications_maize_csv", data_dir / "m_n_publications" / "maize.csv", "Main maize publication database"),
        ("dsm", data_dir / "dsm", "Required local downloaded DSM rasters; no DSM API use"),
        ("ecological_zones", data_dir / "ecological zones", "Required for clipping/cropping DSM to Terai/Churia/Mid-hill"),
        ("boundary", data_dir / "boundary", "Required for ward/municipality/district/province overlay"),
    ]
    rows: list[dict[str, object]] = []
    for name, path, note in required:
        rows.append(
            {
                "input_name": name,
                "path": str(path),
                "exists": path.exists(),
                "type": "directory" if path.is_dir() else "file" if path.is_file() else "missing",
                "note": note,
            }
        )
    return rows


def create_project_structure(project_root: Path, touch_keep: bool = False) -> None:
    created: list[dict[str, str]] = []

    # Top-level folders
    for folder in TOP_LEVEL_FOLDERS:
        make_dir(project_root / folder, created)

    # Data folders
    for folder in DATA_SUBFOLDERS:
        make_dir(project_root / "Data" / folder, created)

    # Output stage folders
    for stage in STAGES:
        stage_dir = project_root / "outputs" / f"{stage.stage_no}_{stage.folder.split('_', 1)[1]}"
        # The expression above keeps the explicit numeric stage and avoids accidental double numbering.
        # Example: 00_harmonized_trial_data
        if not stage_dir.name.startswith(stage.stage_no):
            stage_dir = project_root / "outputs" / stage.folder
        make_dir(stage_dir, created)
        for sub in STAGE_SUBFOLDERS:
            make_dir(stage_dir / sub, created)
        if touch_keep:
            for sub in [stage_dir, *(stage_dir / s for s in STAGE_SUBFOLDERS)]:
                touch_gitkeep(sub)

    # Shared folders for logs and run metadata
    make_dir(project_root / "outputs" / "_run_metadata", created)
    make_dir(project_root / "outputs" / "_shared_lookup_tables", created)

    # Manifests/config
    outputs_dir = project_root / "outputs"

    write_csv(
        outputs_dir / "_project_folder_manifest.csv",
        created,
        ["path", "created_now", "exists_after"],
    )

    stage_rows = [
        {
            "stage_no": s.stage_no,
            "stage_folder": s.folder,
            "stage_label": s.label,
            "main_input": s.main_input,
            "main_output": s.main_output,
            "data_dir": str(outputs_dir / s.folder / "00_data"),
            "tables_dir": str(outputs_dir / s.folder / "01_descriptive_tables"),
            "plots_dir": str(outputs_dir / s.folder / "02_plots"),
            "report_dir": str(outputs_dir / s.folder / "03_stage_report"),
            "next_stage_input_dir": str(outputs_dir / s.folder / "04_inputs_for_next_stage"),
        }
        for s in STAGES
    ]
    write_csv(
        outputs_dir / "_stage_io_map.csv",
        stage_rows,
        [
            "stage_no",
            "stage_folder",
            "stage_label",
            "main_input",
            "main_output",
            "data_dir",
            "tables_dir",
            "plots_dir",
            "report_dir",
            "next_stage_input_dir",
        ],
    )

    required_rows = inspect_required_inputs(project_root)
    write_csv(
        outputs_dir / "00_harmonized_trial_data" / "01_descriptive_tables" / "stage00_required_input_check.csv",
        required_rows,
        ["input_name", "path", "exists", "type", "note"],
    )

    config = build_project_config(project_root)
    (outputs_dir / "_project_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme = outputs_dir / "_run_metadata" / "00_setup_project_README.md"
    readme.write_text(
        "# Soil Advisory project setup\n\n"
        f"Project root: `{project_root}`\n\n"
        "This setup script creates the stage-wise folder structure and manifests. "
        "It does not delete input data and does not call external APIs.\n\n"
        "Run order starts with:\n\n"
        "```text\n"
        "00_setup_project.py\n"
        "0a_prepare_input_inventory.py\n"
        "0b...\n"
        "```\n\n"
        "Soil data policy:\n"
        "1. Use publication-reported soil values first.\n"
        "2. Fill missing values from locally downloaded DSM layers in `Data/dsm`.\n"
        "3. Preserve native DSM resolution.\n"
        "4. Do not call the NARC DSM API.\n"
        "5. Use ISRIC only for supplemental soil variables not available from local DSM.\n",
        encoding="utf-8",
    )

    logger.info("Created/checked %s folders", len(created))
    logger.info("Wrote folder manifest: %s", outputs_dir / "_project_folder_manifest.csv")
    logger.info("Wrote stage IO map: %s", outputs_dir / "_stage_io_map.csv")
    logger.info("Wrote project config: %s", outputs_dir / "_project_config.json")

    missing_inputs = [row for row in required_rows if not row["exists"]]
    if missing_inputs:
        logger.warning("Some expected inputs are missing. See stage00_required_input_check.csv")
        for row in missing_inputs:
            logger.warning("Missing: %s -> %s", row["input_name"], row["path"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Soil Advisory project folders and manifests.")
    parser.add_argument(
        "--project-root",
        default=os.environ.get("SOIL_ADVISORY_ROOT", DEFAULT_PROJECT_ROOT),
        help="Project root folder. Default: C:\\SOIL ADVISORY or SOIL_ADVISORY_ROOT env var.",
    )
    parser.add_argument(
        "--touch-gitkeep",
        action="store_true",
        help="Add empty .gitkeep files to created output folders.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root)
    log_path = project_root / "logs" / "00_setup_project.log"
    setup_logging(log_path)

    logger.info("Starting project setup")
    logger.info("Project root: %s", project_root)

    create_project_structure(project_root, touch_keep=args.touch_gitkeep)

    logger.info("Project setup complete")


if __name__ == "__main__":
    main()
