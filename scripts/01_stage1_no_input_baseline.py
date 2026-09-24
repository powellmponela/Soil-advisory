from pathlib import Path
import pandas as pd
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

def main():
    args = C.parser_for("Stage 1: no-input farmer baseline (N0-P0-K0)").parse_args()
    long = C.load_long(args.workbook)
    x = long[long["treatment_class"] == "CONTROL_000"].copy()
    x = x.rename(columns={"yield_kg_ha": "yield_000_kg_ha"})
    x["N_input_kg_ha"] = 0.0

    C.write_stage_outputs(
        x, Path(args.out) / "stage1_no_input",
        "stage1_no_input",
        ["yield_000_kg_ha", "N_input_kg_ha"]
    )

if __name__ == "__main__":
    main()
