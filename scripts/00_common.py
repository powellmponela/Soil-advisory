from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

RESPONSE_SHEET = "Response_Contrast_Table"

META = [
    "trial_year_id", "trial_id", "year", "study", "variety_block",
    "district", "site", "latitude", "longitude", "spatial_eligible"
]

def read_response_table(workbook: str | Path) -> pd.DataFrame:
    df = pd.read_excel(workbook, sheet_name=RESPONSE_SHEET)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _norm(s) -> str:
    return str(s).strip().lower().replace("–", "-").replace("—", "-")

def classify_treatment(treatment, n_rate) -> str:
    s = _norm(treatment)
    try:
        n = float(n_rate)
    except Exception:
        n = np.nan

    # Special systems first
    if "fym" in s and np.isfinite(n) and abs(n - 60) < 1:
        return "FYM_N60"
    if "fym" in s and np.isfinite(n) and abs(n - 120) < 1:
        return "FYM_N120"

    if "pcu" in s and np.isfinite(n) and abs(n - 60) < 1:
        return "PCU_N60"
    if "pcu" in s and np.isfinite(n) and abs(n - 120) < 1:
        return "PCU_N120"

    if "udp" in s and np.isfinite(n) and abs(n - 78) < 2:
        return "UDP_N78"
    if "udp" in s and np.isfinite(n) and abs(n - 120) < 1:
        return "UDP_N120"

    if "v6/v10" in s:
        return "TIMING_V6V10"
    if "v8" in s and np.isfinite(n) and abs(n - 120) < 1:
        return "TIMING_V8"

    if any(k in s for k in ["micronutrient", "zn +", "znso", "zn support", "zinc"]):
        return "ZN_SUPPORT"
    if any(k in s for k in ["k and s", "k/s treatment", "k/s support"]):
        return "KS_SUPPORT"

    # Baselines
    if np.isfinite(n) and abs(n) < 0.1:
        if "control" in s or "n0-p0-k0" in s:
            return "CONTROL_000"
        if "n omission" in s or "n0-p60-k40" in s:
            return "N0_PK"

    # Mineral N rates with balanced P and K
    if np.isfinite(n) and abs(n - 60) < 1:
        if "n60" in s or s == "n60":
            return "MINERAL_N60"

    if np.isfinite(n) and abs(n - 120) < 1:
        if any(k in s for k in [
            "n120 benchmark", "conventional split npk",
            "full npk", "n120-p60-k40"
        ]):
            return "GOVT_N120"

    if np.isfinite(n) and abs(n - 180) < 1:
        return "MINERAL_N180"
    if np.isfinite(n) and abs(n - 210) < 1:
        return "MINERAL_N210"

    return "OTHER"

def build_treatment_long(response: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for side in ["benchmark", "comparator"]:
        cols = {
            f"{side}_code": "treatment_code",
            f"{side}_treatment": "treatment",
            f"{side}_N_kg_ha": "N_kg_ha",
            f"{side}_yield_t_ha": "yield_t_ha",
        }
        present_meta = [c for c in META if c in response.columns]
        present_cols = [c for c in cols if c in response.columns]
        x = response[present_meta + present_cols].copy()
        x = x.rename(columns=cols)
        x["source_side"] = side
        pieces.append(x)

    long = pd.concat(pieces, ignore_index=True)
    long["yield_t_ha"] = pd.to_numeric(long["yield_t_ha"], errors="coerce")
    long["N_kg_ha"] = pd.to_numeric(long["N_kg_ha"], errors="coerce")
    long["treatment_class"] = [
        classify_treatment(t, n) for t, n in zip(long["treatment"], long["N_kg_ha"])
    ]

    keys = ["trial_year_id", "treatment_class"]
    agg = {
        "trial_id": "first",
        "year": "first",
        "study": "first",
        "variety_block": "first",
        "district": "first",
        "site": "first",
        "latitude": "median",
        "longitude": "median",
        "spatial_eligible": "max",
        "treatment_code": "first",
        "treatment": "first",
        "N_kg_ha": "median",
        "yield_t_ha": "median",
        "source_side": "count",
    }
    agg = {k: v for k, v in agg.items() if k in long.columns}

    out = (
        long[long["treatment_class"] != "OTHER"]
        .groupby(keys, as_index=False, dropna=False)
        .agg(agg)
        .rename(columns={"source_side": "n_source_rows"})
    )
    out["yield_kg_ha"] = out["yield_t_ha"] * 1000.0
    return out

def load_long(workbook: str | Path) -> pd.DataFrame:
    return build_treatment_long(read_response_table(workbook))

def treatment_wide(long: pd.DataFrame, classes: list[str]) -> pd.DataFrame:
    x = long[long["treatment_class"].isin(classes)].copy()
    meta = [
        "trial_year_id", "trial_id", "year", "study", "variety_block",
        "district", "site", "latitude", "longitude", "spatial_eligible"
    ]
    meta = [c for c in meta if c in x.columns]
    base = x.groupby("trial_year_id", as_index=False)[meta[1:]].first()

    y = x.pivot_table(
        index="trial_year_id", columns="treatment_class",
        values="yield_kg_ha", aggfunc="median"
    ).reset_index()
    n = x.pivot_table(
        index="trial_year_id", columns="treatment_class",
        values="N_kg_ha", aggfunc="median"
    ).reset_index()
    n = n.rename(columns={c: f"{c}_N" for c in n.columns if c != "trial_year_id"})
    return base.merge(y, on="trial_year_id", how="outer").merge(n, on="trial_year_id", how="outer")

def add_ae(df: pd.DataFrame, y_col: str, n_col: str, baseline_col: str = "N0_PK", out_col: str = "AE_N"):
    n = pd.to_numeric(df[n_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    y0 = pd.to_numeric(df[baseline_col], errors="coerce")
    df[out_col] = np.where(n > 0, (y - y0) / n, np.nan)
    # yields are already kg/ha, so units = kg grain per kg N
    return df

def add_pfp(df: pd.DataFrame, y_col: str, n_col: str, out_col: str):
    n = pd.to_numeric(df[n_col], errors="coerce")
    y = pd.to_numeric(df[y_col], errors="coerce")
    df[out_col] = np.where(n > 0, y / n, np.nan)
    return df

def retention(alt_y, ref_y):
    a = pd.to_numeric(alt_y, errors="coerce")
    r = pd.to_numeric(ref_y, errors="coerce")
    return np.where(r > 0, a / r, np.nan)


def summarise(df: pd.DataFrame, values: list[str], group_cols) -> pd.DataFrame:
    vals = [v for v in values if v in df.columns]
    groups = [g for g in group_cols if g in df.columns]
    if not vals:
        return pd.DataFrame()
    if not groups:
        groups = []

    rows = []
    if groups:
        grouped = df.groupby(groups, dropna=False)
    else:
        grouped = [((), df)]

    for keys, g in grouped:
        if groups:
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = dict(zip(groups, keys))
        else:
            row = {}

        row["n_trial_years"] = g["trial_year_id"].nunique() if "trial_year_id" in g else len(g)
        row["n_sites"] = g["site"].nunique() if "site" in g else np.nan

        for v in vals:
            s = pd.to_numeric(g[v], errors="coerce").dropna()
            row[f"{v}__n"] = len(s)
            row[f"{v}__mean"] = s.mean() if len(s) else np.nan
            row[f"{v}__median"] = s.median() if len(s) else np.nan
            row[f"{v}__sd"] = s.std(ddof=1) if len(s) > 1 else np.nan
            row[f"{v}__q25"] = s.quantile(0.25) if len(s) else np.nan
            row[f"{v}__q75"] = s.quantile(0.75) if len(s) else np.nan
            row[f"{v}__min"] = s.min() if len(s) else np.nan
            row[f"{v}__max"] = s.max() if len(s) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def write_stage_outputs(df: pd.DataFrame, outdir: str | Path, stem: str, values: list[str]):
    """
    Write outputs without pooling studies or years before stage estimates are calculated.

    Output hierarchy:
      1. trial/site rows (finest analytical unit)
      2. study x year
      3. study x year x district
      4. study x year x district x site
      5. study across years (secondary)
      6. district x year across studies (secondary, only for later spatial overview)

    The primary summaries for interpretation are study_year and study_year_district.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    # Finest unit: one stage estimate per trial-year/site where data exist.
    df.to_csv(out / f"{stem}_trial_site.csv", index=False)

    # PRIMARY: every study, every year kept separate.
    study_year = summarise(df, values, ("study", "year"))
    study_year.to_csv(out / f"{stem}_study_year.csv", index=False)

    study_year_district = summarise(df, values, ("study", "year", "district"))
    study_year_district.to_csv(out / f"{stem}_study_year_district.csv", index=False)

    study_year_district_site = summarise(df, values, ("study", "year", "district", "site"))
    study_year_district_site.to_csv(out / f"{stem}_study_year_district_site.csv", index=False)

    # SECONDARY summaries. These should never replace the primary study-year outputs.
    study_all_years = summarise(df, values, ("study",))
    study_all_years.to_csv(out / f"{stem}_study_all_years.csv", index=False)

    district_year = summarise(df, values, ("district", "year"))
    district_year.to_csv(out / f"{stem}_district_year_across_studies.csv", index=False)

def parser_for(stage: str):
    p = argparse.ArgumentParser(description=stage)
    p.add_argument("workbook", help="Path to NSAF_spatial_trial_and_response_contrast_datasets.xlsx")
    p.add_argument("--out", default="output_descriptives", help="Output root directory")
    p.add_argument("--retention", type=float, default=0.95, help="Yield-retention threshold")
    return p
