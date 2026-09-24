"""Run the Soil Advisory Python workflow sequentially and write per-script logs."""

from __future__ import annotations

import csv
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(r"D:\dss\SOIL ADVISORY")
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOG_DIR = PROJECT_ROOT / "logs" / "full_python_run"

SCRIPTS = [
    "00_setup_project.py",
    "0a_prepare_input_inventory.py",
    "0b_aez_spatial_join_to_maize.py",
    "0c_nsaf_data_legacy.py",
    "1a_extract_narc_data_representative.py",
    "1b_extract_narc_western_coarse.py",
    "1c_extract_narc_western_highres_primary.py",
    "2a_match_2018_trials_to_narc.py",
    "2b_match_2019_demos_and_controls.py",
    "2c_assign_farmer_ids.py",
    "3a_summarize_farmers.py",
    "3b_count_unique_sites.py",
    "3c_count_sites_per_pixel.py",
    "3d_count_farmers_per_pixel.py",
    "3e_check_pixel_coverage.py",
    "4a_run_quefts_representative.py",
    "4b_run_quefts_western_coarse.py",
    "4c_run_quefts_western_highres_primary.py",
    "5a_analyze_2018_n_efficiency_by_pk.py",
    "5b_analyze_2019_demos.py",
    "5c_analyze_2019_n_response.py",
    "5d_compare_cimmyt_strategies.py",
    "6_consolidate_3year_trials.py",
    "7_train_nue_rf_model.py",
    "8_generate_spatial_impact_maps.py",
]

# Deliberately excluded:
# - 9_calculate_national_impact.py
# - 99_run_full_pipeline_reference.py
# - 0a_organize_literature.py (moves files)
# - 0b_clean_personal_info.py (modifies data and outputs)
# - helper modules beginning with "_"


def run_workflow() -> int:
    """Run scripts in order, stopping at the first failure."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []

    for script_name in SCRIPTS:
        script_path = SCRIPTS_DIR / script_name
        log_path = LOG_DIR / f"{script_path.stem}.log"
        print(f"\nRUNNING: {script_name}")

        if not script_path.exists():
            print(f"FAILED: script not found: {script_path}")
            summary.append(
                {
                    "script": script_name,
                    "status": "MISSING",
                    "return_code": "",
                    "elapsed_seconds": "",
                }
            )
            break

        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.perf_counter() - started

        log_text = (
            f"Script: {script_name}\n"
            f"Return code: {result.returncode}\n"
            f"Elapsed seconds: {elapsed:.2f}\n\n"
            "STDOUT\n======\n"
            f"{result.stdout}\n\n"
            "STDERR\n======\n"
            f"{result.stderr}\n"
        )
        log_path.write_text(log_text, encoding="utf-8")

        status = "PASSED" if result.returncode == 0 else "FAILED"
        summary.append(
            {
                "script": script_name,
                "status": status,
                "return_code": result.returncode,
                "elapsed_seconds": round(elapsed, 2),
            }
        )
        print(f"{status}: {script_name} ({elapsed:.2f} seconds)")

        if result.returncode != 0:
            print(f"Inspect the log: {log_path}")
            if result.stderr:
                print(result.stderr[-2000:])
            break

    summary_path = LOG_DIR / "run_summary.csv"
    headers = ["script", "status", "return_code", "elapsed_seconds"]
    with summary_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(summary)

    passed = sum(row["status"] == "PASSED" for row in summary)
    print(f"\nPassed: {passed}/{len(SCRIPTS)}")
    print(f"Summary: {summary_path}")
    return 0 if passed == len(SCRIPTS) else 1


if __name__ == "__main__":
    raise SystemExit(run_workflow())