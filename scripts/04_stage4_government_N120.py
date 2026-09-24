from pathlib import Path
import numpy as np
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

def main():
    args = C.parser_for("Stage 4: government recommendation, N120-P-K").parse_args()
    long = C.load_long(args.workbook)
    x = C.treatment_wide(long, ["CONTROL_000", "N0_PK", "FYM_N60", "GOVT_N120"])
    x = x[x["GOVT_N120"].notna()].copy()

    x["yield_govt_N120_kg_ha"] = x["GOVT_N120"]
    x["yield_0PK_kg_ha"] = x["N0_PK"]
    x["yield_000_kg_ha"] = x["CONTROL_000"]
    x["yield_FYM_N60_kg_ha"] = x["FYM_N60"]
    x["N_input_kg_ha"] = 120.0

    x["N_response_vs_0PK_kg_ha"] = x["yield_govt_N120_kg_ha"] - x["yield_0PK_kg_ha"]
    x["AE_N_kg_grain_per_kg_N"] = x["N_response_vs_0PK_kg_ha"] / 120.0
    x["PFP_N_kg_grain_per_kg_N"] = x["yield_govt_N120_kg_ha"] / 120.0
    x["package_gain_vs_000_kg_ha"] = x["yield_govt_N120_kg_ha"] - x["yield_000_kg_ha"]

    x["increment_vs_FYM_N60_kg_ha"] = x["yield_govt_N120_kg_ha"] - x["yield_FYM_N60_kg_ha"]
    x["extra_mineral_N_vs_FYM_kg_ha"] = 60.0
    x["marginal_grain_per_extra_mineral_N_vs_FYM"] = x["increment_vs_FYM_N60_kg_ha"] / 60.0
    x["FYM60_retention_vs_govt"] = C.retention(x["yield_FYM_N60_kg_ha"], x["yield_govt_N120_kg_ha"])
    x["downward_shift_candidate_kg_N_ha"] = np.where(
        x["FYM60_retention_vs_govt"] >= args.retention, 60.0, 0.0
    )

    C.write_stage_outputs(
        x, Path(args.out) / "stage4_government_N120",
        "stage4_government_N120",
        ["yield_govt_N120_kg_ha", "N_response_vs_0PK_kg_ha",
         "AE_N_kg_grain_per_kg_N", "PFP_N_kg_grain_per_kg_N",
         "package_gain_vs_000_kg_ha", "increment_vs_FYM_N60_kg_ha",
         "marginal_grain_per_extra_mineral_N_vs_FYM",
         "downward_shift_candidate_kg_N_ha"]
    )

if __name__ == "__main__":
    main()
