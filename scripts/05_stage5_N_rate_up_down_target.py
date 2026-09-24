from pathlib import Path
import numpy as np
import pandas as pd
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

RATE_CLASSES = {
    0: "N0_PK",
    60: "MINERAL_N60",
    120: "GOVT_N120",
    180: "MINERAL_N180",
    210: "MINERAL_N210",
}

def choose_target(row, threshold):
    avail = []
    for n, cls in RATE_CLASSES.items():
        y = row.get(cls)
        if pd.notna(y):
            avail.append((n, float(y)))
    if not avail:
        return pd.Series({"observed_max_yield_kg_ha": np.nan,
                          "target_N_kg_ha": np.nan,
                          "yield_at_target_kg_ha": np.nan})
    max_y = max(y for _, y in avail)
    eligible = [(n, y) for n, y in avail if y >= threshold * max_y]
    target_n, target_y = min(eligible, key=lambda z: z[0])
    return pd.Series({
        "observed_max_yield_kg_ha": max_y,
        "target_N_kg_ha": float(target_n),
        "yield_at_target_kg_ha": float(target_y),
    })

def main():
    args = C.parser_for("Stage 5: N-rate target adjustment up or down").parse_args()
    long = C.load_long(args.workbook)
    classes = list(RATE_CLASSES.values())
    x = C.treatment_wide(long, classes)
    x = x[x[classes].notna().sum(axis=1) >= 2].copy()

    chosen = x.apply(lambda r: choose_target(r, args.retention), axis=1)
    x = pd.concat([x, chosen], axis=1)

    x["target_shift_vs_govt_kg_N_ha"] = x["target_N_kg_ha"] - 120.0
    x["N_saving_vs_govt_kg_ha"] = np.maximum(0.0, 120.0 - x["target_N_kg_ha"])
    x["N_increase_vs_govt_kg_ha"] = np.maximum(0.0, x["target_N_kg_ha"] - 120.0)
    x["target_retention_of_observed_max"] = C.retention(
        x["yield_at_target_kg_ha"], x["observed_max_yield_kg_ha"]
    )

    if "N0_PK" in x.columns:
        for n, cls in RATE_CLASSES.items():
            if n > 0 and cls in x.columns:
                x[f"AE_N{n}_kg_grain_per_kg_N"] = (x[cls] - x["N0_PK"]) / float(n)

    C.write_stage_outputs(
        x, Path(args.out) / "stage5_N_rate_target",
        "stage5_N_rate_target",
        ["observed_max_yield_kg_ha", "target_N_kg_ha", "yield_at_target_kg_ha",
         "target_shift_vs_govt_kg_N_ha", "N_saving_vs_govt_kg_ha",
         "N_increase_vs_govt_kg_ha", "target_retention_of_observed_max",
         "AE_N60_kg_grain_per_kg_N", "AE_N120_kg_grain_per_kg_N",
         "AE_N180_kg_grain_per_kg_N", "AE_N210_kg_grain_per_kg_N"]
    )

if __name__ == "__main__":
    main()
