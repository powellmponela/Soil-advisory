from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "01_stage1_no_input_baseline.py",
    "02_stage2_0PK_baseline.py",
    "03_stage3_FYM_N60_farmer_practice.py",
    "04_stage4_government_N120.py",
    "05_stage5_N_rate_up_down_target.py",
    "06_stage6_efficiency_alternatives.py",
    "07_audit_study_year_stage_availability.py",
]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("workbook")
    p.add_argument("--out", default="output_descriptives")
    p.add_argument("--retention", type=float, default=0.95)
    args = p.parse_args()

    here = Path(__file__).resolve().parent
    for script in SCRIPTS:
        cmd = [
            sys.executable, str(here / script), args.workbook,
            "--out", args.out, "--retention", str(args.retention)
        ]
        print("RUN:", " ".join(cmd))
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
