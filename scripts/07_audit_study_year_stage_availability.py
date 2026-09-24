from pathlib import Path
import argparse
import pandas as pd
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

STAGE_REQUIREMENTS = {
    "stage1_000": {"CONTROL_000"},
    "stage2_0PK": {"N0_PK"},
    "stage3_FYM_N60": {"FYM_N60"},
    "stage4_Govt_N120": {"GOVT_N120"},
    "stage5_N_rate": {"N0_PK", "GOVT_N120"},  # minimum screen; more rates improve inference
    "stage6_efficiency": {
        "TIMING_V6V10", "TIMING_V8", "ZN_SUPPORT", "KS_SUPPORT",
        "UDP_N78", "UDP_N120", "PCU_N60", "PCU_N120"
    },
}

def main():
    p = argparse.ArgumentParser(description="Audit stage availability for every study-year.")
    p.add_argument("workbook")
    p.add_argument("--out", default="output_descriptives")
    p.add_argument("--retention", type=float, default=0.95, help="Common workflow option; not used by the audit.")
    args = p.parse_args()

    long = C.load_long(args.workbook)
    rows = []
    for (study, year), g in long.groupby(["study", "year"], dropna=False):
        classes = set(g["treatment_class"].dropna())
        row = {
            "study": study,
            "year": year,
            "n_trial_years": g["trial_year_id"].nunique(),
            "n_sites": g["site"].nunique() if "site" in g.columns else None,
            "treatment_classes_present": ";".join(sorted(classes)),
        }
        row["stage1_000_available"] = "CONTROL_000" in classes
        row["stage2_0PK_available"] = "N0_PK" in classes
        row["stage3_FYM_N60_available"] = "FYM_N60" in classes
        row["stage4_Govt_N120_available"] = "GOVT_N120" in classes
        rate_count = len(classes.intersection(
            {"N0_PK", "MINERAL_N60", "GOVT_N120", "MINERAL_N180", "MINERAL_N210"}
        ))
        row["stage5_N_rate_available"] = rate_count >= 2
        row["stage5_n_rate_levels_present"] = rate_count
        row["stage6_efficiency_available"] = bool(classes.intersection(
            {"TIMING_V6V10", "TIMING_V8", "ZN_SUPPORT", "KS_SUPPORT",
             "UDP_N78", "UDP_N120", "PCU_N60", "PCU_N120"}
        ))
        rows.append(row)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).sort_values(["study", "year"]).to_csv(
        out / "study_year_stage_availability.csv", index=False
    )

if __name__ == "__main__":
    main()
