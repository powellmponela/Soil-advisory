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
EXPECTED_STRATEGIES = ["GR", "N60", "N180", "N210", "TIMING_V6_V10", "FYM_N60", "PCU_N120", "PCU_N60", "UDP_N78"]
GR_N_RATE = 120.0
RANDOM_STATE = 20260924
LOSS_FRACTION = None

TARGETS = {
    "AE_N_kg_grain_per_kg_N": "ae_n",
    "AE_N_ratio_to_GR": "ae_ratio",
    "yield_gain_over_0PK_kg_ha": "yield_gain_0pk",
    "yield_difference_from_GR_kg_ha": "yield_diff_gr",
    "yield_retention_fraction": "yield_retention",
}


def environmental_support(train_x, pred_x):
    lo = train_x.min(axis=0)
    hi = train_x.max(axis=0)
    return ((pred_x >= lo) & (pred_x <= hi)).all(axis=1)


def safe_equivalent_n(reference_n, ae_ratio):
    """N required to generate the same N-attributable yield gain as the reference.

    AE ratio = AE_strategy / AE_reference. Therefore equivalent N required under
    the strategy is reference_N / AE_ratio. Values are undefined where the
    predicted ratio is non-positive.
    """
    reference_n = np.asarray(reference_n, dtype=float)
    ae_ratio = np.asarray(ae_ratio, dtype=float)
    out = np.full(reference_n.shape, np.nan, dtype=float)
    ok = np.isfinite(reference_n) & np.isfinite(ae_ratio) & (reference_n >= 0) & (ae_ratio > 0)
    out[ok] = reference_n[ok] / ae_ratio[ok]
    return out


def main():
    tr = pd.read_csv(TRAINING)
    q = pd.read_csv(QUEFTS)
    missing = [c for c in FEATURES if c not in tr.columns or c not in q.columns]
    if missing:
        raise ValueError("Missing spatial predictors: " + ", ".join(missing))

    q = q.dropna(subset=FEATURES + ["quefts_N_kg_ha", "target_yield_t_ha"]).copy()
    outputs = []
    diagnostics = []

    present_training = set(tr["strategy"].dropna().astype(str).unique())
    for strategy in EXPECTED_STRATEGIES:
        if strategy not in present_training:
            diagnostics.append({"strategy": strategy, "n_training_rows": 0, "n_complete_rows": 0, "n_site_years": 0, "status": "absent_from_stage5a_training"})

    for strategy, s0 in tr.groupby("strategy"):
        needed = FEATURES + list(TARGETS)
        # Model eligibility is based on complete response/covariate data only.
        # The 95% GR-yield-retention criterion is NOT a training filter.
        # It is retained later as a post-prediction interpretation flag.
        s = s0.dropna(subset=needed).copy()
        n_sites = s[["year", "site"]].drop_duplicates().shape[0]
        n_training_rows = len(s0)
        n_complete_rows = len(s)
        if n_sites < MIN_SITE_YEARS:
            diagnostics.append({"strategy": strategy, "n_training_rows": n_training_rows, "n_complete_rows": n_complete_rows, "n_site_years": n_sites, "status": "not_modelled_too_few_site_years"})
            continue

        X = s[FEATURES].to_numpy(float)
        groups = s["site"].astype(str).to_numpy()
        n_splits = min(5, len(np.unique(groups)))
        if n_splits < 2:
            diagnostics.append({"strategy": strategy, "n_site_years": n_sites, "status": "not_modelled_too_few_groups"})
            continue
        cv = GroupKFold(n_splits=n_splits)

        models = {}
        stats = {"strategy": strategy, "n_training_rows": n_training_rows, "n_complete_rows": n_complete_rows, "n_site_years": n_sites, "status": "modelled"}
        for target, label in TARGETS.items():
            y = s[target].to_numpy(float)
            m = RandomForestRegressor(n_estimators=600, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1)
            yp = cross_val_predict(m, X, y, cv=cv, groups=groups, n_jobs=-1)
            stats[f"{label}_cv_r2"] = r2_score(y, yp)
            stats[f"{label}_cv_rmse"] = mean_squared_error(y, yp) ** 0.5
            m.fit(X, y)
            models[label] = m
        diagnostics.append(stats)

        Xp = q[FEATURES].to_numpy(float)
        support = environmental_support(X, Xp)

        z = q.copy()
        z["strategy"] = strategy
        strategy_rate = float(pd.to_numeric(s0.get("N_rate_kg_ha"), errors="coerce").dropna().median())
        z["strategy_N_rate_kg_ha"] = strategy_rate
        z["tested_N_change_vs_GR_kg_ha"] = strategy_rate - GR_N_RATE

        z["predicted_AE_N_kg_grain_per_kg_N"] = np.clip(models["ae_n"].predict(Xp), -50.0, 150.0)
        z["predicted_AE_N_ratio_to_GR"] = np.clip(models["ae_ratio"].predict(Xp), 0.05, 5.0)
        z["predicted_yield_gain_over_0PK_kg_ha"] = models["yield_gain_0pk"].predict(Xp)
        z["predicted_yield_difference_from_GR_kg_ha"] = models["yield_diff_gr"].predict(Xp)
        z["predicted_yield_retention_fraction"] = np.clip(models["yield_retention"].predict(Xp), 0.0, 1.5)
        z["environmental_support"] = support

        # ------------------------------------------------------------------
        # Equivalent-yield N requirement relative to the observed GR benchmark.
        # This is the primary N reduction/increase metric requested for advisory.
        # It answers: how much N would this strategy require to produce the same
        # N-attributable yield gain as GR, given its predicted AE-N relative to GR?
        # ------------------------------------------------------------------
        z["N_required_for_GR_equivalent_yield_kg_ha"] = safe_equivalent_n(
            np.full(len(z), GR_N_RATE), z["predicted_AE_N_ratio_to_GR"]
        )
        z["N_change_at_GR_equivalent_yield_kg_ha"] = z["N_required_for_GR_equivalent_yield_kg_ha"] - GR_N_RATE
        z["N_reduction_at_GR_equivalent_yield_kg_ha"] = np.maximum(
            0.0, -z["N_change_at_GR_equivalent_yield_kg_ha"]
        )
        z["N_increase_at_GR_equivalent_yield_kg_ha"] = np.maximum(
            0.0, z["N_change_at_GR_equivalent_yield_kg_ha"]
        )
        z["N_change_at_GR_equivalent_yield_pct"] = 100.0 * z["N_change_at_GR_equivalent_yield_kg_ha"] / GR_N_RATE

        # ------------------------------------------------------------------
        # Equivalent-yield N requirement for each QUEFTS target-yield scenario.
        # QUEFTS gives the reference N demand at the target yield. The predicted
        # AE ratio scales the N required by the alternative strategy to achieve
        # the same target-yield response as the reference management.
        # ------------------------------------------------------------------
        z["reference_N_demand_kg_ha"] = z["quefts_N_kg_ha"]
        z["N_required_for_same_target_yield_kg_ha"] = safe_equivalent_n(
            z["reference_N_demand_kg_ha"], z["predicted_AE_N_ratio_to_GR"]
        )
        z["N_change_for_same_target_yield_kg_ha"] = (
            z["N_required_for_same_target_yield_kg_ha"] - z["reference_N_demand_kg_ha"]
        )
        z["N_reduction_for_same_target_yield_kg_ha"] = np.maximum(
            0.0, -z["N_change_for_same_target_yield_kg_ha"]
        )
        z["N_increase_for_same_target_yield_kg_ha"] = np.maximum(
            0.0, z["N_change_for_same_target_yield_kg_ha"]
        )
        z["N_change_for_same_target_yield_pct"] = np.where(
            z["reference_N_demand_kg_ha"] > 0,
            100.0 * z["N_change_for_same_target_yield_kg_ha"] / z["reference_N_demand_kg_ha"],
            np.nan,
        )

        # Keep the observed/predicted yield comparison as supporting evidence,
        # but do not use a 95% threshold to define N reduction.
        z["retains_95pct_GR"] = z["predicted_yield_retention_fraction"] >= 0.95
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

    summary = pred.groupby(["province", "district", "target_yield_t_ha", "strategy"], dropna=False).agg(
        n_pixels=("lat", "size"),
        supported_pixels=("environmental_support", "sum"),
        median_predicted_AE_N=("predicted_AE_N_kg_grain_per_kg_N", "median"),
        median_predicted_yield_gain_over_0PK_kg_ha=("predicted_yield_gain_over_0PK_kg_ha", "median"),
        median_predicted_yield_difference_from_GR_kg_ha=("predicted_yield_difference_from_GR_kg_ha", "median"),
        strategy_N_rate_kg_ha=("strategy_N_rate_kg_ha", "first"),
        tested_N_change_vs_GR_kg_ha=("tested_N_change_vs_GR_kg_ha", "first"),
        median_N_required_for_GR_equivalent_yield=("N_required_for_GR_equivalent_yield_kg_ha", "median"),
        median_N_change_at_GR_equivalent_yield=("N_change_at_GR_equivalent_yield_kg_ha", "median"),
        median_N_reduction_at_GR_equivalent_yield=("N_reduction_at_GR_equivalent_yield_kg_ha", "median"),
        median_N_increase_at_GR_equivalent_yield=("N_increase_at_GR_equivalent_yield_kg_ha", "median"),
        median_reference_N_kg_ha=("reference_N_demand_kg_ha", "median"),
        median_N_required_for_same_target_yield=("N_required_for_same_target_yield_kg_ha", "median"),
        median_N_change_for_same_target_yield=("N_change_for_same_target_yield_kg_ha", "median"),
        median_N_reduction_for_same_target_yield=("N_reduction_for_same_target_yield_kg_ha", "median"),
        median_N_increase_for_same_target_yield=("N_increase_for_same_target_yield_kg_ha", "median"),
        median_N_change_for_same_target_yield_pct=("N_change_for_same_target_yield_pct", "median"),
        median_predicted_yield_retention=("predicted_yield_retention_fraction", "median"),
        median_predicted_AE_ratio=("predicted_AE_N_ratio_to_GR", "median")
    ).reset_index()
    summary.to_csv(SUMMARY, index=False)

    print(PRED)
    print(SUMMARY)
    print(DIAG)


if __name__ == "__main__":
    main()
