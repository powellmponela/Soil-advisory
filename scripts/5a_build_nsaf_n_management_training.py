from pathlib import Path
import re
import numpy as np
import pandas as pd

ROOT = Path(r"D:\dss\SOIL ADVISORY")
HARM = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize" / "harmonised" / "nsaf_maize_key_variables.csv"
DSM = ROOT / "Data" / "dsm_western_terai_midhill_pixel-centroid.csv"
OUT = ROOT / "outputs" / "spatial_extrapolation"
OUT.mkdir(parents=True, exist_ok=True)

# AE-N is retained for conventional N-rate/timing comparisons because 0PK is the
# explicit N-omission reference. PFP-N is used for PCU, UDP and FYM strategies.
STRATEGIES = {
    "0PK": {"rate": 0.0, "method": "reference"},
    "GR": {"rate": 120.0, "method": "AE"},
    "N60": {"rate": 60.0, "method": "AE"},
    "N180": {"rate": 180.0, "method": "AE"},
    "N210": {"rate": 210.0, "method": "AE"},
    "TIMING_V6_V10": {"rate": 120.0, "method": "AE"},
    "FYM_N60": {"rate": 60.0, "method": "PFP"},
    "PCU_N120": {"rate": 120.0, "method": "PFP"},
    "PCU_N60": {"rate": 60.0, "method": "PFP"},
    "UDP_N78": {"rate": 78.0, "method": "PFP"},
}


def norm_text(x):
    if pd.isna(x):
        return ""
    s = str(x).strip().lower()
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s


def classify_strategy(row):
    # Combine all available descriptors so harmonisation-label differences do not
    # silently remove valid treatments.
    fields = []
    for c in ["treatment", "treatment_role", "source_treatment_label", "treatment_code"]:
        if c in row.index:
            fields.append(norm_text(row.get(c)))
    t = " | ".join(fields)

    if ("n0-p60-k40" in t or "n omission" in t) and "fym" not in t and "pcu" not in t and "udp" not in t:
        return "0PK"
    if "v6/v10" in t or ("v6" in t and "v10" in t):
        return "TIMING_V6_V10"
    if "fym" in t and ("n60" in t or re.search(r"\bn\s*60\b", t)):
        return "FYM_N60"
    if "pcu" in t and ("n120" in t or re.search(r"\bn\s*120\b", t)):
        return "PCU_N120"
    if "pcu" in t and ("n60" in t or re.search(r"\bn\s*60\b", t)):
        return "PCU_N60"
    if "udp" in t and ("n78" in t or re.search(r"\bn\s*78\b", t)):
        return "UDP_N78"
    if "n210-p60-k40" in t or re.search(r"\bn\s*210\b", t):
        return "N210"
    if "n180-p60-k40" in t or re.search(r"\bn\s*180\b", t):
        return "N180"
    if "n60-p60-k40" in t or re.search(r"\bn\s*60\b", t):
        return "N60"
    if "n120-p60-k40" in t or "conventional split npk" in t or "government recommendation" in t:
        return "GR"
    return np.nan


def nearest_dsm(training, dsm):
    dsm = dsm.dropna(subset=["lat", "lon"]).copy()
    mean_lat = np.deg2rad(pd.concat([training["latitude"], dsm["lat"]]).mean())
    dx = dsm["lon"].to_numpy(float) * 111_320.0 * np.cos(mean_lat)
    dy = dsm["lat"].to_numpy(float) * 110_540.0
    rows = []
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
        for c in ["ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg", "sand_pct", "clay_pct", "silt_pct"]:
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
    q = df[df["strategy"].notna()].copy()
    q["yield_kg_ha"] = pd.to_numeric(q[ycol], errors="coerce")
    q["latitude"] = pd.to_numeric(q["latitude"], errors="coerce")
    q["longitude"] = pd.to_numeric(q["longitude"], errors="coerce")

    pre = q.groupby("strategy", dropna=False).agg(
        n_records=("strategy", "size"),
        n_site_years=("site", "size"),
    ).reset_index()
    pre.to_csv(OUT / "nsaf_strategy_pre_pair_counts.csv", index=False)

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

    missing_rows = []
    rows = []
    for _, r in wide.iterrows():
        gr = r.get("GR", np.nan)
        zero_pk = r.get("0PK", np.nan)
        if pd.isna(gr):
            missing_rows.append({**{k: r[k] for k in keys}, "missing_reference": "GR"})
            continue

        pfp_gr = gr / 120.0 if gr > 0 else np.nan
        ae_gr = (gr - zero_pk) / 120.0 if pd.notna(zero_pk) else np.nan

        for strategy, meta in STRATEGIES.items():
            if strategy == "0PK":
                continue
            y = r.get(strategy, np.nan)
            if pd.isna(y):
                continue
            rate = meta["rate"]
            method = meta["method"]
            if rate <= 0:
                continue

            # AE-N strategies require 0PK. PFP strategies do not; this is the key
            # change allowing PCU, UDP and FYM to use their valid GR-paired data.
            if method == "AE" and pd.isna(zero_pk):
                missing_rows.append({**{k: r[k] for k in keys}, "strategy": strategy, "missing_reference": "0PK"})
                continue

            ae = (y - zero_pk) / rate if pd.notna(zero_pk) else np.nan
            pfp = y / rate
            row = {
                **{k: r[k] for k in keys},
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "strategy": strategy,
                "efficiency_metric": method,
                "N_rate_kg_ha": rate,
                "yield_0PK_kg_ha": zero_pk,
                "yield_kg_ha": y,
                "yield_GR_kg_ha": gr,
                "yield_gain_over_0PK_kg_ha": y - zero_pk if pd.notna(zero_pk) else np.nan,
                "yield_difference_from_GR_kg_ha": y - gr,
                "yield_retention_fraction": y / gr if gr > 0 else np.nan,
                "AE_N_kg_grain_per_kg_N": ae,
                "AE_N_GR_kg_grain_per_kg_N": ae_gr,
                "delta_AE_N_from_GR": ae - ae_gr if pd.notna(ae) and pd.notna(ae_gr) else np.nan,
                "AE_N_ratio_to_GR": ae / ae_gr if pd.notna(ae) and pd.notna(ae_gr) and ae_gr > 0 else np.nan,
                "PFP_N_kg_grain_per_kg_N": pfp,
                "PFP_N_GR_kg_grain_per_kg_N": pfp_gr,
                "delta_PFP_N_from_GR": pfp - pfp_gr if pd.notna(pfp_gr) else np.nan,
                "PFP_N_ratio_to_GR": pfp / pfp_gr if pd.notna(pfp_gr) and pfp_gr > 0 else np.nan,
                "tested_N_change_vs_GR_kg_ha": rate - 120.0,
            }
            rows.append(row)

    pd.DataFrame(missing_rows).to_csv(OUT / "nsaf_siteyears_missing_0PK_or_GR.csv", index=False)

    training = pd.DataFrame(rows)
    if training.empty:
        raise ValueError("No matched GR-strategy site-years were found.")

    dsm = pd.read_csv(DSM)
    training = nearest_dsm(training, dsm)
    training["spatial_training_eligible"] = training["dsm_match_distance_km"] <= 5.0
    training.to_csv(OUT / "nsaf_n_management_spatial_training.csv", index=False)

    summary = training.groupby(["strategy", "efficiency_metric"], dropna=False).agg(
        n_site_years=("site", "size"),
        spatially_eligible=("spatial_training_eligible", "sum"),
        tested_N_rate_kg_ha=("N_rate_kg_ha", "median"),
        median_yield_difference_from_GR_kg_ha=("yield_difference_from_GR_kg_ha", "median"),
        median_yield_retention=("yield_retention_fraction", "median"),
        median_AE_N=("AE_N_kg_grain_per_kg_N", "median"),
        median_PFP_N=("PFP_N_kg_grain_per_kg_N", "median"),
        median_AE_ratio_to_GR=("AE_N_ratio_to_GR", "median"),
        median_PFP_ratio_to_GR=("PFP_N_ratio_to_GR", "median"),
    ).reset_index()
    summary.to_csv(OUT / "nsaf_n_management_strategy_summary.csv", index=False)

    print("Strategy records after pairing:")
    print(summary.to_string(index=False))
    print(f"\nSaved {len(training)} site-year-strategy records.")
    print(OUT / "nsaf_n_management_spatial_training.csv")
    print(OUT / "nsaf_n_management_strategy_summary.csv")


if __name__ == "__main__":
    main()
