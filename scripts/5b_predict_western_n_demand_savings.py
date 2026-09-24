from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import r2_score, mean_squared_error

ROOT = Path(r"D:\dss\SOIL ADVISORY")
OUT = ROOT / "outputs" / "spatial_extrapolation"
TRAINING = OUT / "nsaf_n_management_spatial_training.csv"
QUEFTS = ROOT / "outputs" / "maize_quefts_western_highres_pixels.csv"
PRED = OUT / "western_n_demand_savings_pixels.csv"
SUMMARY = OUT / "western_n_demand_savings_district.csv"
DIAG = OUT / "western_spatial_model_diagnostics.csv"

FEATURES = ["ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg", "sand_pct", "clay_pct", "silt_pct"]
MIN_SITE_YEARS = 12
GR_N_RATE = 120.0
RANDOM_STATE = 20260924
LOSS_FRACTION = None
EXPECTED = ["GR", "N60", "N180", "N210", "TIMING_V6_V10", "FYM_N60", "PCU_N120", "PCU_N60", "UDP_N78"]

AE_STRATEGIES = {"GR", "N60", "N180", "N210", "TIMING_V6_V10"}
PFP_STRATEGIES = {"FYM_N60", "PCU_N120", "PCU_N60", "UDP_N78"}

COMMON_TARGETS = {
    "yield_difference_from_GR_kg_ha": "yield_diff_gr",
    "yield_retention_fraction": "yield_retention",
}
AE_TARGETS = {
    "AE_N_kg_grain_per_kg_N": "ae_n",
    "AE_N_ratio_to_GR": "eff_ratio",
    "yield_gain_over_0PK_kg_ha": "yield_gain_0pk",
}
PFP_TARGETS = {
    "PFP_N_kg_grain_per_kg_N": "pfp_n",
    "PFP_N_ratio_to_GR": "eff_ratio",
}


def environmental_support(train_x, pred_x):
    lo = train_x.min(axis=0)
    hi = train_x.max(axis=0)
    return ((pred_x >= lo) & (pred_x <= hi)).all(axis=1)


def safe_equivalent_n(reference_n, efficiency_ratio):
    reference_n = np.asarray(reference_n, dtype=float)
    efficiency_ratio = np.asarray(efficiency_ratio, dtype=float)
    out = np.full(reference_n.shape, np.nan, dtype=float)
    ok = np.isfinite(reference_n) & np.isfinite(efficiency_ratio) & (reference_n >= 0) & (efficiency_ratio > 0)
    out[ok] = reference_n[ok] / efficiency_ratio[ok]
    return out


def safe_target_n_from_pfp(target_yield_t_ha, pfp_n):
    y = np.asarray(target_yield_t_ha, dtype=float) * 1000.0
    pfp = np.asarray(pfp_n, dtype=float)
    out = np.full(y.shape, np.nan, dtype=float)
    ok = np.isfinite(y) & np.isfinite(pfp) & (y >= 0) & (pfp > 0)
    out[ok] = y[ok] / pfp[ok]
    return out


def fit_model(X, y, groups, cv):
    m = RandomForestRegressor(n_estimators=600, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1)
    yp = cross_val_predict(m, X, y, cv=cv, groups=groups, n_jobs=-1)
    r2 = r2_score(y, yp)
    rmse = mean_squared_error(y, yp) ** 0.5
    m.fit(X, y)
    return m, r2, rmse


def main():
    tr = pd.read_csv(TRAINING)
    q = pd.read_csv(QUEFTS)
    missing = [c for c in FEATURES if c not in tr.columns or c not in q.columns]
    if missing:
        raise ValueError("Missing spatial predictors: " + ", ".join(missing))

    q = q.dropna(subset=FEATURES + ["quefts_N_kg_ha", "target_yield_t_ha"]).copy()
    outputs = []
    diagnostics = []

    present = set(tr["strategy"].dropna().astype(str).unique())
    for strategy in EXPECTED:
        if strategy not in present:
            diagnostics.append({"strategy": strategy, "n_site_years": 0, "status": "absent_from_stage5a_training"})

    for strategy, s0 in tr.groupby("strategy"):
        metric = "PFP" if strategy in PFP_STRATEGIES else "AE"
        targets = dict(COMMON_TARGETS)
        targets.update(PFP_TARGETS if metric == "PFP" else AE_TARGETS)
        needed = FEATURES + list(targets)
        s = s0.dropna(subset=needed).copy()
        n_sites = s[["year", "site"]].drop_duplicates().shape[0]
        if n_sites < MIN_SITE_YEARS:
            diagnostics.append({"strategy": strategy, "efficiency_metric": metric, "n_site_years": n_sites, "status": "not_modelled_too_few_site_years"})
            continue

        X = s[FEATURES].to_numpy(float)
        groups = s["site"].astype(str).to_numpy()
        n_splits = min(5, len(np.unique(groups)))
        if n_splits < 2:
            diagnostics.append({"strategy": strategy, "efficiency_metric": metric, "n_site_years": n_sites, "status": "not_modelled_too_few_groups"})
            continue
        cv = GroupKFold(n_splits=n_splits)

        models = {}
        stats = {"strategy": strategy, "efficiency_metric": metric, "n_site_years": n_sites, "status": "modelled"}
        for target, label in targets.items():
            m, r2, rmse = fit_model(X, s[target].to_numpy(float), groups, cv)
            stats[f"{label}_cv_r2"] = r2
            stats[f"{label}_cv_rmse"] = rmse
            models[label] = m
        diagnostics.append(stats)

        Xp = q[FEATURES].to_numpy(float)
        support = environmental_support(X, Xp)
        z = q.copy()
        z["strategy"] = strategy
        z["efficiency_metric"] = metric
        strategy_rate = float(pd.to_numeric(s0["N_rate_kg_ha"], errors="coerce").dropna().median())
        z["strategy_N_rate_kg_ha"] = strategy_rate
        z["tested_N_change_vs_GR_kg_ha"] = strategy_rate - GR_N_RATE
        z["environmental_support"] = support

        z["predicted_yield_difference_from_GR_kg_ha"] = models["yield_diff_gr"].predict(Xp)
        z["predicted_yield_retention_fraction"] = np.clip(models["yield_retention"].predict(Xp), 0.0, 1.5)
        z["retains_95pct_GR"] = z["predicted_yield_retention_fraction"] >= 0.95

        # Initialize both efficiency families so downstream tables have stable columns.
        z["predicted_AE_N_kg_grain_per_kg_N"] = np.nan
        z["predicted_PFP_N_kg_grain_per_kg_N"] = np.nan
        z["predicted_efficiency_ratio_to_GR"] = np.clip(models["eff_ratio"].predict(Xp), 0.05, 5.0)
        z["predicted_yield_gain_over_0PK_kg_ha"] = np.nan

        if metric == "AE":
            z["predicted_AE_N_kg_grain_per_kg_N"] = np.clip(models["ae_n"].predict(Xp), -50.0, 150.0)
            z["predicted_yield_gain_over_0PK_kg_ha"] = models["yield_gain_0pk"].predict(Xp)
            # Equivalent N relative to GR based on AE ratio.
            z["N_required_for_GR_equivalent_yield_kg_ha"] = safe_equivalent_n(
                np.full(len(z), GR_N_RATE), z["predicted_efficiency_ratio_to_GR"]
            )
            # For QUEFTS target-yield scenarios, scale the reference demand by AE ratio.
            z["N_required_for_same_target_yield_kg_ha"] = safe_equivalent_n(
                z["quefts_N_kg_ha"], z["predicted_efficiency_ratio_to_GR"]
            )
        else:
            z["predicted_PFP_N_kg_grain_per_kg_N"] = np.clip(models["pfp_n"].predict(Xp), 0.01, 250.0)
            # PFP directly relates total grain yield to mineral-N input. For GR-equivalent
            # yield use the PFP ratio; for an explicit target yield use Y_target/PFP.
            z["N_required_for_GR_equivalent_yield_kg_ha"] = safe_equivalent_n(
                np.full(len(z), GR_N_RATE), z["predicted_efficiency_ratio_to_GR"]
            )
            z["N_required_for_same_target_yield_kg_ha"] = safe_target_n_from_pfp(
                z["target_yield_t_ha"], z["predicted_PFP_N_kg_grain_per_kg_N"]
            )

        z["reference_N_demand_kg_ha"] = z["quefts_N_kg_ha"]
        z["N_change_at_GR_equivalent_yield_kg_ha"] = z["N_required_for_GR_equivalent_yield_kg_ha"] - GR_N_RATE
        z["N_reduction_at_GR_equivalent_yield_kg_ha"] = np.maximum(0.0, -z["N_change_at_GR_equivalent_yield_kg_ha"])
        z["N_increase_at_GR_equivalent_yield_kg_ha"] = np.maximum(0.0, z["N_change_at_GR_equivalent_yield_kg_ha"])

        z["N_change_for_same_target_yield_kg_ha"] = z["N_required_for_same_target_yield_kg_ha"] - z["reference_N_demand_kg_ha"]
        z["N_reduction_for_same_target_yield_kg_ha"] = np.maximum(0.0, -z["N_change_for_same_target_yield_kg_ha"])
        z["N_increase_for_same_target_yield_kg_ha"] = np.maximum(0.0, z["N_change_for_same_target_yield_kg_ha"])
        z["N_change_for_same_target_yield_pct"] = np.where(
            z["reference_N_demand_kg_ha"] > 0,
            100.0 * z["N_change_for_same_target_yield_kg_ha"] / z["reference_N_demand_kg_ha"],
            np.nan,
        )
        z["advisory_evidence_supported"] = z["environmental_support"]

        if LOSS_FRACTION is not None:
            z["estimated_N_loss_reduction_kg_ha"] = z["N_reduction_for_same_target_yield_kg_ha"] * float(LOSS_FRACTION)
            z["loss_reduction_assumption_fraction"] = float(LOSS_FRACTION)
        else:
            z["estimated_N_loss_reduction_kg_ha"] = np.nan
            z["loss_reduction_assumption_fraction"] = np.nan
        outputs.append(z)

    if not outputs:
        raise RuntimeError("No strategy had enough site-year evidence for spatial modelling.")

    pred = pd.concat(outputs, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pred.to_csv(PRED, index=False)
    pd.DataFrame(diagnostics).to_csv(DIAG, index=False)

    summary = pred.groupby(["province", "district", "target_yield_t_ha", "strategy", "efficiency_metric"], dropna=False).agg(
        n_pixels=("lat", "size"),
        supported_pixels=("environmental_support", "sum"),
        median_predicted_AE_N=("predicted_AE_N_kg_grain_per_kg_N", "median"),
        median_predicted_PFP_N=("predicted_PFP_N_kg_grain_per_kg_N", "median"),
        median_predicted_yield_difference_from_GR_kg_ha=("predicted_yield_difference_from_GR_kg_ha", "median"),
        strategy_N_rate_kg_ha=("strategy_N_rate_kg_ha", "first"),
        median_reference_N_kg_ha=("reference_N_demand_kg_ha", "median"),
        median_N_required_for_same_target_yield=("N_required_for_same_target_yield_kg_ha", "median"),
        median_N_change_for_same_target_yield=("N_change_for_same_target_yield_kg_ha", "median"),
        median_N_reduction_for_same_target_yield=("N_reduction_for_same_target_yield_kg_ha", "median"),
        median_N_increase_for_same_target_yield=("N_increase_for_same_target_yield_kg_ha", "median"),
        median_predicted_yield_retention=("predicted_yield_retention_fraction", "median"),
        median_efficiency_ratio_to_GR=("predicted_efficiency_ratio_to_GR", "median"),
    ).reset_index()
    summary.to_csv(SUMMARY, index=False)

    print("\nModel diagnostics:")
    print(pd.DataFrame(diagnostics).to_string(index=False))
    print("\nOutputs:")
    print(PRED)
    print(SUMMARY)
    print(DIAG)


if __name__ == "__main__":
    main()
