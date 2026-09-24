"""QUEFTS-style western Nepal target-yield demand scenarios.

Python replacement for 4c_run_quefts_western_highres_primary.R so the
spatial workflow can run entirely from the existing Python environment.

DSM values are spatial model covariates, not measured soil samples at every
pixel. Missing P or K values are not replaced with zero.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from _quefts import add_quefts_soil_inputs, add_native_supply

ROOT = Path(r"D:\dss\SOIL ADVISORY")
INPUT = ROOT / "Data" / "dsm_western_terai_midhill_pixel-centroid.csv"
OUTPUT = ROOT / "outputs" / "maize_quefts_western_highres_pixels.csv"

TARGET_YIELDS_T_HA = (6.0, 8.0, 10.0)
IE_N = 40.0
IE_P = 200.0
IE_K = 40.0
RE_N = 0.50
RE_P = 0.20
RE_K = 0.50

REQUIRED = [
    "province", "district", "lat", "lon", "ph", "om_pct",
    "p_olsen_mg_kg", "k_exch_mg_kg",
]


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"High-resolution DSM input not found: {INPUT}\n"
            "Run 1c_extract_narc_western_highres_primary.py first."
        )

    baseline = pd.read_csv(INPUT)
    missing = [c for c in REQUIRED if c not in baseline.columns]
    if missing:
        raise ValueError("Missing required DSM columns: " + ", ".join(missing))

    # Keep missing soil information as missing; do not interpret NA as zero supply.
    baseline = add_quefts_soil_inputs(baseline)
    clean = baseline.dropna(subset=["ph", "OC", "P_Olsen", "Exch_K"]).copy()
    if clean.empty:
        raise ValueError("No complete DSM soil records available for QUEFTS modelling.")

    native = add_native_supply(clean)
    required_supply = ["n_supply", "p_supply", "k_supply"]
    missing_supply = [c for c in required_supply if c not in native.columns]
    if missing_supply:
        raise ValueError(
            "_quefts.add_native_supply did not return expected columns: "
            + ", ".join(missing_supply)
        )

    scenarios = []
    for target_t_ha in TARGET_YIELDS_T_HA:
        target_kg_ha = target_t_ha * 1000.0
        n_uptake_req = target_kg_ha / IE_N
        p_uptake_req = target_kg_ha / IE_P
        k_uptake_req = target_kg_ha / IE_K

        z = native.copy()
        z["target_yield_t_ha"] = target_t_ha
        z["quefts_N_kg_ha"] = np.maximum(0.0, (n_uptake_req - z["n_supply"]) / RE_N)
        z["quefts_P2O5_kg_ha"] = np.maximum(0.0, (p_uptake_req - z["p_supply"]) / RE_P) * 2.29
        z["quefts_K2O_kg_ha"] = np.maximum(0.0, (k_uptake_req - z["k_supply"]) / RE_K) * 1.21
        z["IE_N_kg_grain_per_kg_uptake"] = IE_N
        z["RE_N_fraction"] = RE_N
        z["dsm_interpretation"] = "modelled spatial covariate"
        scenarios.append(z)

    results = pd.concat(scenarios, ignore_index=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT, index=False)

    print(f"Input DSM pixels: {len(baseline)}")
    print(f"Complete soil pixels modelled: {len(clean)}")
    print(f"Target-yield scenarios: {list(TARGET_YIELDS_T_HA)} t/ha")
    print(f"Saved {len(results)} pixel-scenarios to {OUTPUT}")
    print("Required downstream columns present:",
          all(c in results.columns for c in ["quefts_N_kg_ha", "target_yield_t_ha"]))


if __name__ == "__main__":
    main()
