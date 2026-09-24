"""Python counterpart of 4a_run_quefts_representative.R."""

from pathlib import Path

import pandas as pd

from _quefts import add_native_supply, add_quefts_soil_inputs, add_target_recommendations

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "Data" / "narc_baseline_maize.csv"
OUTPUT = ROOT / "outputs" / "maize_quefts_recommendations.csv"


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError("Input file not found. Run Python extraction script first.")
    baseline = add_quefts_soil_inputs(pd.read_csv(INPUT))
    clean = baseline.dropna(subset=["ph", "OC", "P_Olsen", "Exch_K"]).copy()
    if clean.empty:
        raise ValueError("No valid soil data for QUEFTS model.")
    results = add_target_recommendations(add_native_supply(clean))
    recommendations = pd.DataFrame({
        "district": results["district_requested"], "lat": results["lat"],
        "lon": results["lon"], "ph": results["ph"], "om_pct": results["om_pct"],
        "native_N_supply_kg_ha": results["n_supply"],
        "native_P_supply_kg_ha": results["p_supply"],
        "native_K_supply_kg_ha": results["k_supply"],
        "rec_N_kg_ha": results["rec_N_kg_ha"],
        "rec_P2O5_kg_ha": results["rec_P2O5_kg_ha"],
        "rec_K2O_kg_ha": results["rec_K2O_kg_ha"],
        "narc_urea_total_kg_ha": results["maize_urea_total"],
        "narc_dap_kg_ha": results["maize_dap"],
        "narc_mop_kg_ha": results["maize_mop"],
    })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(OUTPUT, index=False)
    print(f"QUEFTS modeling completed for {len(recommendations)} locations.")
    print(f"Output saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
