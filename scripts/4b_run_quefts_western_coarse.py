"""Python counterpart of 4b_run_quefts_western_coarse.R."""

from pathlib import Path

import pandas as pd

from _quefts import add_native_supply, add_quefts_soil_inputs, add_target_recommendations

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "Data" / "narc_baseline_maize_pixel_western.csv"
POINTS_OUTPUT = ROOT / "outputs" / "maize_quefts_western_points.csv"
SUMMARY_OUTPUT = ROOT / "outputs" / "maize_quefts_western_advisory.csv"


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError("Western input data not found. Run extraction first.")
    baseline = pd.read_csv(INPUT)
    baseline[["p_olsen_mg_kg", "k_exch_mg_kg"]] = baseline[["p_olsen_mg_kg", "k_exch_mg_kg"]].fillna(0)
    clean = add_quefts_soil_inputs(baseline).dropna(subset=["ph", "OC", "P_Olsen", "Exch_K"])
    if clean.empty:
        raise ValueError("No valid soil data for Western modeling.")
    results = add_target_recommendations(add_native_supply(clean))
    summary = (results.groupby(["province", "district"], dropna=False)
        .agg(n_points=("ph", "size"), avg_ph=("ph", "mean"),
             rec_N=("rec_N_kg_ha", "mean"), rec_P2O5=("rec_P2O5_kg_ha", "mean"),
             rec_K2O=("rec_K2O_kg_ha", "mean")).reset_index())
    summary["avg_ph"] = summary["avg_ph"].round(2)
    summary[["rec_N", "rec_P2O5", "rec_K2O"]] = summary[["rec_N", "rec_P2O5", "rec_K2O"]].round(1)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(POINTS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    print(f"Western advisory completed for {len(results)} pixels and {len(summary)} districts.")


if __name__ == "__main__":
    main()
