from pathlib import Path
import numpy as np
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

def main():
    args = C.parser_for("Stage 3: farmer-practice proxy, FYM + N60").parse_args()
    long = C.load_long(args.workbook)
    x = C.treatment_wide(long, ["N0_PK", "FYM_N60", "GOVT_N120"])
    x = x[x["FYM_N60"].notna()].copy()

    x["yield_FYM_N60_kg_ha"] = x["FYM_N60"]
    x["yield_0PK_kg_ha"] = x["N0_PK"]
    x["yield_govt_N120_kg_ha"] = x["GOVT_N120"]
    x["mineral_N_input_kg_ha"] = 60.0

    x["gain_vs_0PK_kg_ha"] = x["yield_FYM_N60_kg_ha"] - x["yield_0PK_kg_ha"]
    x["PFP_mineral_N_kg_grain_per_kg_N"] = x["yield_FYM_N60_kg_ha"] / 60.0

    x["retention_vs_govt"] = C.retention(x["yield_FYM_N60_kg_ha"], x["yield_govt_N120_kg_ha"])
    x["candidate_N_reduction_vs_govt_kg_ha"] = 60.0
    x["estimated_N_saving_if_retained_kg_ha"] = np.where(
        x["retention_vs_govt"] >= args.retention, 60.0, 0.0
    )

    C.write_stage_outputs(
        x, Path(args.out) / "stage3_FYM_N60",
        "stage3_FYM_N60",
        ["yield_FYM_N60_kg_ha", "yield_0PK_kg_ha", "yield_govt_N120_kg_ha",
         "gain_vs_0PK_kg_ha", "PFP_mineral_N_kg_grain_per_kg_N",
         "retention_vs_govt", "estimated_N_saving_if_retained_kg_ha"]
    )

if __name__ == "__main__":
    main()
