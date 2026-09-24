"""Python counterpart of 5d_compare_cimmyt_strategies.R."""

from pathlib import Path

import numpy as np
import pandas as pd

from _quefts import add_native_supply, add_quefts_soil_inputs, add_target_recommendations

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "Data" / "nsaf_plots_narc_soil.csv"
PLOT_OUTPUT = ROOT / "outputs" / "maize_cimmyt_plot_results.csv"
SUMMARY_OUTPUT = ROOT / "outputs" / "maize_cimmyt_strategy_comparison.csv"


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError("Matched trial/soil file not found.")
    clean = add_quefts_soil_inputs(pd.read_csv(INPUT)).dropna(subset=["ph", "OC", "P_Olsen", "Exch_K"]).copy()
    control = clean.loc[clean["N_kg_ha"] == 0].groupby("District")["Yield_t_ha"].mean()
    clean["yield_control"] = clean["District"].map(control).fillna(2.0)
    results = add_target_recommendations(add_native_supply(clean))
    results["uptake_N_trial"] = results["n_supply"] + results["N_kg_ha"] * 0.5
    results["uptake_P_trial"] = results["p_supply"] + results["P2O5_kg_ha"] / 2.29 * 0.2
    results["uptake_K_trial"] = results["k_supply"] + results["K2O_kg_ha"] / 1.21 * 0.5
    results["yield_trial_pred"] = np.minimum.reduce([
        results["uptake_N_trial"] * 40, results["uptake_P_trial"] * 200,
        results["uptake_K_trial"] * 40]) / 1000
    denominator = np.where(results["N_kg_ha"] > 0, results["N_kg_ha"], 1)
    results["AE_trial"] = (results["Yield_t_ha"] - results["yield_control"]) * 1000 / denominator
    results["NUE_trial"] = results["Yield_t_ha"] * 1000 / denominator
    results = results.rename(columns={"rec_N_kg_ha": "n_rec_quefts", "rec_P2O5_kg_ha": "p_rec_quefts", "rec_K2O_kg_ha": "k_rec_quefts"})
    summary = (results.groupby("District", dropna=False)
        .agg(n_plots=("District", "size"), avg_yield_trial=("Yield_t_ha", "mean"),
             avg_ae_trial=("AE_trial", "mean"), avg_n_applied_trial=("N_kg_ha", "mean"),
             avg_n_rec_quefts=("n_rec_quefts", "mean"), avg_p_rec_quefts=("p_rec_quefts", "mean")).reset_index())
    summary["avg_yield_trial"] = summary["avg_yield_trial"].round(2)
    for col in ["avg_ae_trial", "avg_n_applied_trial", "avg_n_rec_quefts", "avg_p_rec_quefts"]:
        summary[col] = summary[col].round(1)
    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(PLOT_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    print(f"CIMMYT comparison completed for {len(results)} plots across {len(summary)} districts.")


if __name__ == "__main__":
    main()
