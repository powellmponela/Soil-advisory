"""Python counterpart of 5b_analyze_2019_demos.R."""

from pathlib import Path

import numpy as np
import pandas as pd

from _quefts import add_native_supply, add_quefts_soil_inputs, add_target_recommendations

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "Data" / "nsaf_plots_narc_soil_2019.csv"
CONTROLS = ROOT / "Data" / "nsaf_pooled_controls_2017_2019.csv"
PLOT_OUTPUT = ROOT / "outputs" / "maize_2019_demo_plot_results.csv"
SUMMARY_OUTPUT = ROOT / "outputs" / "maize_2019_demo_analysis.csv"


def main() -> None:
    if not INPUT.exists() or not CONTROLS.exists():
        raise FileNotFoundError("Missing input files for 2019 analysis.")
    df = pd.read_csv(INPUT)
    df["Yield_t_ha"] = pd.to_numeric(df["Yield_t_ha"], errors="coerce") / 1000.0
    controls = pd.read_csv(CONTROLS)
    control_baseline = controls.groupby("District", dropna=False)["Yield_t_ha"].mean()
    clean = add_quefts_soil_inputs(df).dropna(subset=["ph", "OC", "P_Olsen", "Exch_K"]).copy()
    clean["yield_control_pooled"] = clean["District"].map(control_baseline).fillna(controls["Yield_t_ha"].mean())
    results = add_target_recommendations(add_native_supply(clean))
    denominator = np.where(results["N_kg_ha"] > 0, results["N_kg_ha"], 1)
    results["AE_pooled"] = (results["Yield_t_ha"] - results["yield_control_pooled"]) * 1000 / denominator
    results["NUE"] = results["Yield_t_ha"] * 1000 / denominator
    results = results.rename(columns={"rec_N_kg_ha": "n_rec_quefts", "rec_P2O5_kg_ha": "p_rec_quefts", "rec_K2O_kg_ha": "k_rec_quefts"})
    summary = (results.groupby("District", dropna=False)
        .agg(n_demos=("District", "size"), avg_yield_2019=("Yield_t_ha", "mean"),
             avg_ae_pooled=("AE_pooled", "mean"), avg_n_applied=("N_kg_ha", "mean"),
             avg_n_rec_quefts=("n_rec_quefts", "mean")).reset_index())
    summary["avg_yield_2019"] = summary["avg_yield_2019"].round(2)
    summary[["avg_ae_pooled", "avg_n_applied", "avg_n_rec_quefts"]] = summary[["avg_ae_pooled", "avg_n_applied", "avg_n_rec_quefts"]].round(1)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(PLOT_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    print(f"2019 demo analysis completed for {len(results)} plots.")


if __name__ == "__main__":
    main()
