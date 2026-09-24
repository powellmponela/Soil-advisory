from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("SOIL_ADVISORY_ROOT", Path(__file__).resolve().parents[1]))
DATA_DIR = BASE_DIR / "Data"
OUTPUT_ROOT = BASE_DIR / "outputs"

M_N_PUBLICATIONS_DIR = DATA_DIR / "m_n_publications"
DSM_DIR = DATA_DIR / "dsm"
ECOLOGICAL_ZONES_DIR = DATA_DIR / "ecological zones"
ECOLOGICAL_ZONES_SHP = ECOLOGICAL_ZONES_DIR / "Cross_sections_of_Nepal_s_physiographic_regions.shp"
BOUNDARY_DIR = DATA_DIR / "boundary"

STAGE_FOLDERS = {
    0: "00_harmonized_trial_data",
    1: "01_trial_response_calibration",
    2: "02_farmer_yield_anchoring",
    3: "03_yield_gap_target_yield",
    4: "04_response_domain_transfer",
    5: "05_nsaf_innovation_targeting",
    6: "06_fertilizer_demand_estimation",
    7: "07_spatial_advisory_ensemble",
    8: "08_admin_aggregation_country",
    99: "99_reports_recommendation_package",
}

STAGE_SUBFOLDERS = [
    "00_data",
    "01_descriptive_tables",
    "02_plots",
    "03_stage_report",
    "04_inputs_for_next_stage",
]


def ensure_stage_dirs(stage_no: int) -> dict[str, Path]:
    """Create and return standard output subfolders for a workflow stage."""
    if stage_no not in STAGE_FOLDERS:
        raise ValueError(f"Unknown stage number: {stage_no}")

    stage_dir = OUTPUT_ROOT / STAGE_FOLDERS[stage_no]
    dirs = {name: stage_dir / name for name in STAGE_SUBFOLDERS}

    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    return dirs


def ensure_all_output_dirs() -> None:
    """Create all numbered stage output folders and their standard subfolders."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    for stage_no in STAGE_FOLDERS:
        ensure_stage_dirs(stage_no)
