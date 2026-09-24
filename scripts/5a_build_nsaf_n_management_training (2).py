from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(r"D:\dss\SOIL ADVISORY")
HARM = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize" / "harmonised" / "nsaf_maize_key_variables.csv"
DSM = ROOT / "Data" / "dsm_western_terai_midhill_pixel-centroid.csv"
OUT = ROOT / "outputs" / "spatial_extrapolation"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_STRATEGIES = [
    "0PK", "GR", "N60", "N180", "N210", "TIMING_V6_V10",
    "FYM_N60", "PCU_N120", "PCU_N60", "UDP_N78",
]

N_RATES = {
    "0PK": 0.0,
    "GR": 120.0,
    "N60": 60.0,
    "N180": 180.0,
    "N210": 210.0,
    "TIMING_V6_V10": 120.0,
    "FYM_N60": 60.0,
    "PCU_N120": 120.0,
    "PCU_N60": 60.0,
    "UDP_N78": 78.0,
}


def _norm(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()
    s = s.replace("₀", "0").replace("₁", "1").replace("₂", "2")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s


def classify_strategy(row):
    """Classify using all available treatment descriptors, not brittle exact text only."""
    cols = ["treatment", "treatment_role", "source_treatment_label", "treatment_code"]
    txt = " | ".join(_norm(row.get(c, "")) for c in cols)

    # Management alternatives first so embedded N rates are not misclassified.
    if "pcu" in txt or "polymer" in txt or "coated urea" in txt or "controlled-release" in txt:
        if re.search(r"\bn\s*120\b", txt) or "n120" in txt:
            return "PCU_N120"
        if re.search(r"\bn\s*60\b", txt) or "n60" in txt:
            return "PCU_N60"

    if "udp" in txt or "deep placement" in txt:
        if re.search(r"\bn\s*78\b", txt) or "n78" in txt:
            return "UDP_N78"

    if "fym" in txt or "farmyard manure" in txt or "manure" in txt:
        if re.search(r"\bn\s*60\b", txt) or "n60" in txt:
            return "FYM_N60"

    if "v6/v10" in txt or ("v6" in txt and "v10" in txt):
        if "n120" in txt or re.search(r"\bn\s*120\b", txt):
            return "TIMING_V6_V10"

    # N omission / 0PK reference.
    if "n omission" in txt or "0pk" in txt or "n0-p60-k40" in txt:
        return "0PK"

    # Conventional GR reference.
    if "conventional split npk" in txt:
        return "GR"
    if "n120-p60-k40" in txt and not any(k in txt for k in ["pcu", "fym", "udp", "v6", "v10"]):
        return "GR"

    # Plain N-rate series only.
    if "n210-p60-k40" in txt:
        return "N210"
    if "n180-p60-k40" in txt:
        return "N180"
    if "n60-p60-k40" in txt and not any(k in txt for k in ["pcu", "fym", "udp"]):
        return "N60"

    return np.nan


def nearest_dsm(training, dsm):
    dsm = dsm.dropna(subset=["lat", "lon"]).copy()
    mean_lat = np.deg2rad(pd.concat([training["latitude"], dsm["lat"]]).mean())
    dx = dsm["lon"].to_numpy(float) * 111_320.0 * np.cos(mean_lat)
    dy = dsm["lat"].to_numpy(float) * 110_540.0
    rows = []
    dsm_cols = [
        "ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg",
        "sand_pct", "clay_pct", "silt_pct",
    ]
    for _, r in training.iterrows():
        if pd.isna(r["latitude"]) or pd.isna(r["longitude"]):
            continue
        x = float(r["longitude"]) * 111_320.0 * np.cos(mean_lat)
        y = float(r["latitude"]) * 110_540.0
        dist = np.sqrt((dx - x) ** 2 + (dy - y) ** 2)
        j = int(np.argmin(dist))
        s = dsm.iloc[j]
        z = r.to_dict()
        z["dsm_match_distance_km"] = float(dist[j] / 1000.0)
        for c in dsm_cols:
            z[c] = s.get(c, np.nan)
        rows.append(z)
    return pd.DataFrame(rows)


def main():
    df = pd.read_csv(HARM)
    ycol = "adjusted_yield_kg_ha" if "adjusted_yield_kg_ha" in df.columns else "yield_14pct_kg_ha"
    required = {"year", "study", "district", "site", "latitude", "longitude", "treatment", ycol}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Missing harmonised columns: " + ", ".join(sorted(missing)))

    df["strategy"] = df.apply(classify_strategy, axis=1)

    # Audit classification before any matching.
    audit_cols = [c for c in ["year", "study", "district", "site", "treatment", "treatment_role", "source_treatment_label", "treatment_code", "strategy"] if c in df.columns]
    df.loc[df["strategy"].notna(), audit_cols].to_csv(OUT / "nsaf_strategy_label_audit.csv", index=False)

    q = df[df["strategy"].notna()].copy()
    q["yield_kg_ha"] = pd.to_numeric(q[ycol], errors="coerce")
    q["latitude"] = pd.to_numeric(q["latitude"], errors="coerce")
    q["longitude"] = pd.to_numeric(q["longitude"], errors="coerce")

    print("\nClassified treatment records:")
    print(q["strategy"].value_counts(dropna=False).reindex(EXPECTED_STRATEGIES).fillna(0).astype(int).to_string())

    keys = ["year", "study", "district", "site"]
    means = q.groupby(keys + ["strategy"], dropna=False).agg(
        mean_yield_kg_ha=("yield_kg_ha", "mean"),
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        n=("yield_kg_ha", "count"),
    ).reset_index()

    wide = means.pivot_table(index=keys, columns="strategy", values="mean_yield_kg_ha", aggfunc="first").reset_index()
    coords = means.groupby(keys, dropna=False).agg(latitude=("latitude", "mean"), longitude=("longitude", "mean")).reset_index()
    wide = wide.merge(coords, on=keys, how="left")

    rows = []
    missing_reference_rows = []
    for _, r in wide.iterrows():
        if pd.isna(r.get("0PK")) or pd.isna(r.get("GR")):
            missing_reference_rows.append({**{k: r[k] for k in keys}, "has_0PK": pd.notna(r.get("0PK")), "has_GR": pd.notna(r.get("GR"))})
            continue

        ae_gr = (r["GR"] - r["0PK"]) / 120.0
        for strategy, rate in N_RATES.items():
            if strategy == "0PK" or pd.isna(r.get(strategy)) or rate <= 0:
                continue
            ae = (r[strategy] - r["0PK"]) / rate
            rows.append({
                **{k: r[k] for k in keys},
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "strategy": strategy,
                "N_rate_kg_ha": rate,
                "yield_0PK_kg_ha": r["0PK"],
                "yield_kg_ha": r[strategy],
                "yield_GR_kg_ha": r["GR"],
                "yield_gain_over_0PK_kg_ha": r[strategy] - r["0PK"],
                "yield_difference_from_GR_kg_ha": r[strategy] - r["GR"],
                "yield_retention_fraction": r[strategy] / r["GR"] if r["GR"] > 0 else np.nan,
                "AE_N_kg_grain_per_kg_N": ae,
                "AE_N_GR_kg_grain_per_kg_N": ae_gr,
                "delta_AE_N_from_GR": ae - ae_gr,
                "AE_N_ratio_to_GR": ae / ae_gr if ae_gr > 0 else np.nan,
                # Descriptive tested-rate difference only; NOT the equivalent-yield saving metric.
                "tested_N_change_vs_GR_kg_ha": rate - 120.0,
            })

    if missing_reference_rows:
        pd.DataFrame(missing_reference_rows).to_csv(OUT / "nsaf_siteyears_missing_0PK_or_GR.csv", index=False)

    training = pd.DataFrame(rows)
    if training.empty:
        raise ValueError("No matched 0PK-GR-strategy site-years were found.")

    dsm = pd.read_csv(DSM)
    training = nearest_dsm(training, dsm)
    training["spatial_training_eligible"] = training["dsm_match_distance_km"] <= 5.0
    training.to_csv(OUT / "nsaf_n_management_spatial_training.csv", index=False)

    summary = training.groupby("strategy", dropna=False).agg(
        n_site_years=("site", "size"),
        spatially_eligible=("spatial_training_eligible", "sum"),
        median_yield_gain_over_0PK_kg_ha=("yield_gain_over_0PK_kg_ha", "median"),
        median_yield_retention=("yield_retention_fraction", "median"),
        median_AE_N=("AE_N_kg_grain_per_kg_N", "median"),
        median_AE_ratio_to_GR=("AE_N_ratio_to_GR", "median"),
        median_delta_AE_N=("delta_AE_N_from_GR", "median"),
        tested_N_rate_kg_ha=("N_rate_kg_ha", "median"),
        tested_N_change_vs_GR_kg_ha=("tested_N_change_vs_GR_kg_ha", "median"),
    ).reset_index()
    summary.to_csv(OUT / "nsaf_n_management_strategy_summary.csv", index=False)

    print("\nMatched 0PK-GR site-year-strategy records:")
    print(training["strategy"].value_counts().reindex([s for s in EXPECTED_STRATEGIES if s != "0PK"]).fillna(0).astype(int).to_string())
    print(f"\nSaved {len(training)} matched site-year-strategy records.")
    print(OUT / "nsaf_n_management_spatial_training.csv")
    print(OUT / "nsaf_n_management_strategy_summary.csv")
    print(OUT / "nsaf_strategy_label_audit.csv")


if __name__ == "__main__":
    main()
