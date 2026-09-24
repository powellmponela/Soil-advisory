from pathlib import Path
import numpy as np
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

def main():
    args = C.parser_for("Stage 2: N0-P-K agronomic baseline").parse_args()
    long = C.load_long(args.workbook)
    x = C.treatment_wide(long, ["CONTROL_000", "N0_PK"])
    x = x[x["N0_PK"].notna()].copy()

    x["yield_0PK_kg_ha"] = x["N0_PK"]
    x["yield_000_kg_ha"] = x["CONTROL_000"]
    x["PK_supported_gain_kg_ha"] = x["yield_0PK_kg_ha"] - x["yield_000_kg_ha"]
    x["PK_supported_gain_pct"] = np.where(
        x["yield_000_kg_ha"] > 0,
        100 * x["PK_supported_gain_kg_ha"] / x["yield_000_kg_ha"],
        np.nan
    )
    x["N_input_kg_ha"] = 0.0

    C.write_stage_outputs(
        x, Path(args.out) / "stage2_0PK",
        "stage2_0PK",
        ["yield_0PK_kg_ha", "yield_000_kg_ha", "PK_supported_gain_kg_ha",
         "PK_supported_gain_pct", "N_input_kg_ha"]
    )

if __name__ == "__main__":
    main()
