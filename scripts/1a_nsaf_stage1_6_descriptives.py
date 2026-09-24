from __future__ import annotations

"""
NSAF maize Stage 1-6 agronomic descriptives.

Project root
------------
D:\dss\SOIL ADVISORY

Input
-----
outputs\summary_maize_by_year_site_treatment.csv

Run
---
python .\scripts\1a_nsaf_stage1_6_descriptives.py

Agronomic conventions
---------------------
- Stage 1: no-input reference, N0-P0-K0.
- Stage 2: N-zero agronomic reference, N0-P60-K40.
- Stage 3: farmer practice, FYM 6 t/ha + N60-P60-K40.
- Stage 4: government-recommended NPK reference, N120-P60-K40.
- Stage 5: mineral-N rate response and N-rate adjustment.
- Stage 6: timing, source, placement and nutrient-management alternatives.

Standard terms used:
- yield response
- relative yield (%)
- agronomic efficiency of N (AE-N)
- partial factor productivity of N (PFP-N)
- marginal yield response
- potential mineral-N reduction
- additional N requirement

No DSM extrapolation or crop-area scaling is applied.
"""

from pathlib import Path
import numpy as np
import pandas as pd

RELATIVE_YIELD_THRESHOLD_PCT = 95.0

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
INPUT = OUTPUTS / "summary_maize_by_year_site_treatment.csv"

OUT_SITE = OUTPUTS / "nsaf_stage1_6_study_year_site.csv"
OUT_SUMMARY = OUTPUTS / "nsaf_stage1_6_study_year_summary.csv"
OUT_TARGET = OUTPUTS / "nsaf_stage5_n_rate_target_by_study_year_site.csv"
OUT_MATRIX = OUTPUTS / "nsaf_stage1_6_availability_matrix.csv"
OUT_QC = OUTPUTS / "nsaf_stage1_6_qc.csv"

STAGE_NAMES = {
    1: "No-input reference",
    2: "N-zero agronomic reference",
    3: "Farmer practice",
    4: "Government-recommended NPK reference",
    5: "N-rate response and adjustment",
    6: "Efficiency and nutrient-management alternatives",
}


def num(s):
    return pd.to_numeric(s, errors="coerce")


def close_to(s, value, tol=0.6):
    return (num(s) - float(value)).abs() <= tol


def initialise(df):
    df = df.copy()

    df["year"] = num(df["year"]).astype("Int64")
    df["treatment_code"] = df["treatment_code"].astype(str).str.strip()
    df["treatment_lc"] = df["treatment"].fillna("").astype(str).str.lower()

    df["study"] = df["source_datasets"].fillna("Unknown source").astype(str)
    df["variety"] = "All maize"

    df["stage"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df["stage_name"] = pd.NA
    df["treatment_role"] = pd.NA

    df["N_kg_ha"] = num(df["mean_N_fertilizer_kg_ha"])
    df["P2O5_kg_ha"] = num(df["mean_P2O5_fertilizer_kg_ha"])
    df["K2O_kg_ha"] = num(df["mean_K2O_fertilizer_kg_ha"])
    df["FYM_t_ha"] = num(df["mean_organic_fertilizer_t_ha"])

    df["mineral_N_rate_response"] = False
    df["government_reference"] = False
    df["AE_N_applicable"] = False
    df["PFP_N_applicable"] = False

    return df


def assign(
    df,
    mask,
    *,
    study=None,
    variety=None,
    stage=None,
    role=None,
    n=None,
    p=None,
    k=None,
    fym=None,
    rate_response=None,
    government_reference=False,
    ae_applicable=False,
    pfp_applicable=False,
):
    if study is not None:
        df.loc[mask, "study"] = study
    if variety is not None:
        df.loc[mask, "variety"] = variety
    if stage is not None:
        df.loc[mask, "stage"] = stage
        df.loc[mask, "stage_name"] = STAGE_NAMES[stage]
    if role is not None:
        df.loc[mask, "treatment_role"] = role
    if n is not None:
        df.loc[mask, "N_kg_ha"] = float(n)
    if p is not None:
        df.loc[mask, "P2O5_kg_ha"] = float(p)
    if k is not None:
        df.loc[mask, "K2O_kg_ha"] = float(k)
    if fym is not None:
        df.loc[mask, "FYM_t_ha"] = float(fym)
    if rate_response is not None:
        df.loc[mask, "mineral_N_rate_response"] = bool(rate_response)
    if government_reference:
        df.loc[mask, "government_reference"] = True
    if ae_applicable:
        df.loc[mask, "AE_N_applicable"] = True
    if pfp_applicable:
        df.loc[mask, "PFP_N_applicable"] = True


def classify_2017(df):
    y = df["year"].eq(2017)
    code = df["treatment_code"]

    df.loc[y, "study"] = "2017 core trial"
    df.loc[y, "variety"] = "All maize"

    mapping = {
        "1":  (1, "N0-P0-K0", 0,   0,  0, False, False, False),
        "2":  (2, "N0-P60-K40", 0, 60, 40, True,  False, False),
        "5":  (5, "N60-P60-K40", 60, 60, 40, True, True, True),
        "6":  (4, "N120-P60-K40", 120, 60, 40, True, True, True),
        "7":  (5, "N180-P60-K40", 180, 60, 40, True, True, True),
        "8":  (5, "N210-P60-K40", 210, 60, 40, True, True, True),
        "9":  (6, "N120-P60-K40 + micronutrients", 120, 60, 40, False, True, True),
        "10": (6, "N120-P60-K40 + K/S", 120, 60, 40, False, True, True),
    }

    for c, (stage, role, n, p, k, rate, ae, pfp) in mapping.items():
        m = y & code.eq(c)
        assign(
            df, m,
            stage=stage,
            role=role,
            n=n, p=p, k=k,
            rate_response=rate,
            government_reference=(c == "6"),
            ae_applicable=ae,
            pfp_applicable=pfp,
        )


def classify_2018(df):
    y = df["year"].eq(2018)
    name = df["treatment_lc"]
    n = df["N_kg_ha"]
    p = df["P2O5_kg_ha"]
    k = df["K2O_kg_ha"]
    fym = df["FYM_t_ha"]

    df.loc[y, "study"] = "2018 N source, timing and FYM trial"
    df.loc[y, "variety"] = "All maize"

    # Stage 1: N0-P0-K0
    m = y & close_to(n, 0) & close_to(p, 0) & close_to(k, 0)
    assign(df, m, stage=1, role="N0-P0-K0", n=0, p=0, k=0)

    # Stage 2: N0-P60-K40
    m = y & close_to(n, 0) & close_to(p, 60) & close_to(k, 40)
    assign(
        df, m,
        stage=2,
        role="N0-P60-K40",
        n=0, p=60, k=40,
        rate_response=True,
    )

    # Stage 3: FYM + N60 farmer practice.
    m = y & close_to(n, 60) & (fym.fillna(0) > 0)
    assign(
        df, m,
        stage=3,
        role="FYM 6 t/ha + N60-P60-K40",
        n=60, p=60, k=40, fym=6,
        ae_applicable=False,
        pfp_applicable=False,
    )

    # Stage 4: government-recommended conventional N120-P60-K40.
    altered_n120 = (
        name.str.contains("pcu", regex=False)
        | name.str.contains("udp", regex=False)
        | name.str.contains("v6/v10", regex=False)
        | (fym.fillna(0) > 0)
    )
    m = (
        y
        & close_to(n, 120)
        & close_to(p, 60)
        & close_to(k, 40)
        & ~altered_n120
    )
    assign(
        df, m,
        stage=4,
        role="N120-P60-K40",
        n=120, p=60, k=40,
        rate_response=True,
        government_reference=True,
        ae_applicable=True,
        pfp_applicable=True,
    )

    # Stage 5: conventional mineral N60 rate.
    altered_n60 = (
        name.str.contains("pcu", regex=False)
        | name.str.contains("udp", regex=False)
        | (fym.fillna(0) > 0)
    )
    m = (
        y
        & close_to(n, 60)
        & close_to(p, 60)
        & close_to(k, 40)
        & ~altered_n60
    )
    assign(
        df, m,
        stage=5,
        role="N60-P60-K40",
        n=60, p=60, k=40,
        rate_response=True,
        ae_applicable=True,
        pfp_applicable=True,
    )

    # Stage 6: timing/source/placement alternatives.
    m = y & name.str.contains("v6/v10", regex=False)
    assign(
        df, m,
        stage=6,
        role="N120-P60-K40 at V6/V10",
        n=120, p=60, k=40,
        ae_applicable=True,
        pfp_applicable=True,
    )

    m = y & name.str.contains("pcu", regex=False) & close_to(n, 120)
    assign(
        df, m,
        stage=6,
        role="PCU N120-P60-K40",
        n=120, p=60, k=40,
        ae_applicable=True,
        pfp_applicable=True,
    )

    m = y & name.str.contains("pcu", regex=False) & close_to(n, 60)
    assign(
        df, m,
        stage=6,
        role="PCU N60-P60-K40",
        n=60, p=60, k=40,
        ae_applicable=True,
        pfp_applicable=True,
    )

    m = y & name.str.contains("udp", regex=False)
    assign(
        df, m,
        stage=6,
        role="UDP N78-P60-K40",
        n=78, p=60, k=40,
        ae_applicable=True,
        pfp_applicable=True,
    )


def classify_2019(df):
    y = df["year"].eq(2019)
    code = df["treatment_code"]

    # T1-T10 core trial.
    core = y & code.str.match(r"^T\d+$", na=False)
    df.loc[core, "study"] = "2019 T1-T10 core trial"
    df.loc[core, "variety"] = "All maize"

    mapping = {
        "T1":  (1, "N0-P0-K0", 0,   False, False, False),
        "T2":  (2, "N0-P60-K40", 0,  True,  False, False),
        "T5":  (5, "N60-P60-K40", 60, True,  True,  True),
        "T6":  (4, "N120-P60-K40", 120, True, True, True),
        "T7":  (5, "N180-P60-K40", 180, True, True, True),
        "T8":  (5, "N210-P60-K40", 210, True, True, True),
        "T9":  (6, "N120-P60-K40 at V8", 120, False, True, True),
        "T10": (6, "N120-P60-K40 at V6/V10", 120, False, True, True),
    }

    for c, (stage, role, nrate, rate, ae, pfp) in mapping.items():
        m = y & code.eq(c)
        assign(
            df, m,
            stage=stage,
            role=role,
            n=nrate,
            p=0 if c == "T1" else 60,
            k=0 if c == "T1" else 40,
            rate_response=rate,
            government_reference=(c == "T6"),
            ae_applicable=ae,
            pfp_applicable=pfp,
        )

    # Established project mapping: A = Hybrid, B = OPV.
    blocks = {
        "A": ("2019 Hybrid strategy block", "Hybrid"),
        "B": ("2019 OPV strategy block", "OPV"),
    }

    for prefix, (study, variety) in blocks.items():
        block = y & code.str.match(rf"^{prefix}[1-5]$", na=False)
        df.loc[block, "study"] = study
        df.loc[block, "variety"] = variety

        roles = {
            f"{prefix}1": (4, f"{variety} N120-P60-K40", 120, 0, True, True),
            f"{prefix}2": (6, f"{variety} FYM 6 t/ha + N120-P60-K40", 120, 6, False, False),
            f"{prefix}3": (6, f"{variety} Zn + N120-P60-K40", 120, 0, False, True),
            f"{prefix}4": (6, f"{variety} PCU N60-P60-K40", 60, 0, False, True),
            f"{prefix}5": (6, f"{variety} UDP N78-P60-K40", 78, 0, False, True),
        }

        for c, (stage, role, nrate, fymrate, govt, pfp) in roles.items():
            m = y & code.eq(c)
            assign(
                df, m,
                study=study,
                variety=variety,
                stage=stage,
                role=role,
                n=nrate, p=60, k=40, fym=fymrate,
                government_reference=govt,
                ae_applicable=False,  # no N0-P-K reference within these blocks
                pfp_applicable=pfp,
            )


def add_agronomic_metrics(stage):
    keys = ["study", "year", "variety", "site"]

    # Government-recommended NPK reference within the same experimental unit.
    gov = (
        stage[stage["government_reference"]]
        .groupby(keys, as_index=False, dropna=False)
        .agg(
            government_reference_yield_kg_ha=("mean_yield_kg_ha", "mean"),
            government_reference_N_kg_ha=("N_kg_ha", "mean"),
        )
    )

    stage = stage.merge(gov, on=keys, how="left")
    stage["government_reference_available"] = (
        stage["government_reference_yield_kg_ha"].notna()
    )

    y = num(stage["mean_yield_kg_ha"])
    yref = num(stage["government_reference_yield_kg_ha"])
    n = num(stage["N_kg_ha"])
    nref = num(stage["government_reference_N_kg_ha"])

    # Relative yield to the government-recommended NPK reference.
    stage["relative_yield_to_government_reference_pct"] = np.where(
        yref > 0,
        100.0 * y / yref,
        np.nan,
    )

    # Yield response relative to N120 reference.
    stage["yield_response_vs_government_reference_kg_ha"] = np.where(
        stage["government_reference_available"],
        y - yref,
        np.nan,
    )

    # N-rate difference relative to government reference.
    stage["N_rate_difference_vs_government_reference_kg_ha"] = np.where(
        stage["government_reference_available"],
        n - nref,
        np.nan,
    )

    # Potential mineral-N reduction applies only to lower-N alternatives.
    stage["potential_mineral_N_reduction_applicable"] = (
        stage["stage"].isin([3, 5, 6])
        & stage["government_reference_available"]
        & (n < nref)
    )

    stage["potential_mineral_N_reduction_kg_ha"] = np.where(
        stage["potential_mineral_N_reduction_applicable"]
        & (
            stage["relative_yield_to_government_reference_pct"]
            >= RELATIVE_YIELD_THRESHOLD_PCT
        ),
        nref - n,
        np.nan,
    )

    # If a lower-N alternative is tested but relative yield is below threshold,
    # retain an explicit zero potential reduction rather than NA.
    tested_lower = (
        stage["potential_mineral_N_reduction_applicable"]
        & (
            stage["relative_yield_to_government_reference_pct"]
            < RELATIVE_YIELD_THRESHOLD_PCT
        )
    )
    stage.loc[tested_lower, "potential_mineral_N_reduction_kg_ha"] = 0.0

    # Stage 2 N0-P-K reference for AE-N.
    n0pk = (
        stage[stage["stage"].eq(2)]
        .groupby(keys, as_index=False, dropna=False)
        .agg(N0_PK_reference_yield_kg_ha=("mean_yield_kg_ha", "mean"))
    )
    stage = stage.merge(n0pk, on=keys, how="left")

    y0 = num(stage["N0_PK_reference_yield_kg_ha"])

    stage["yield_response_to_N_kg_ha"] = np.where(
        stage["AE_N_applicable"] & y0.notna(),
        y - y0,
        np.nan,
    )

    # Agronomic efficiency of N (kg grain increase per kg N applied).
    stage["AE_N_kg_grain_per_kg_N"] = np.where(
        stage["AE_N_applicable"] & (n > 0) & y0.notna(),
        (y - y0) / n,
        np.nan,
    )

    # Partial factor productivity of N.
    # Omitted for FYM treatments because organic N input is not quantified here.
    stage["PFP_N_kg_grain_per_kg_N"] = np.where(
        stage["PFP_N_applicable"] & (n > 0),
        y / n,
        np.nan,
    )

    return stage


def build_stage5_n_rate_targets(stage):
    """
    For each study/year/variety/site, select the lowest TESTED mineral-N rate
    achieving >=95% relative yield to the maximum observed yield in the tested
    N-rate response.

    This is a trial-based target-setting screen, not an economic optimum.
    """
    keys = ["study", "year", "variety", "site"]
    rate = stage[stage["mineral_N_rate_response"]].copy()

    rows = []

    for key_vals, g in rate.groupby(keys, dropna=False):
        g = g.dropna(subset=["N_kg_ha", "mean_yield_kg_ha"]).copy()
        if g.empty:
            continue

        curve = (
            g.groupby("N_kg_ha", as_index=False)
            .agg(yield_kg_ha=("mean_yield_kg_ha", "mean"))
            .sort_values("N_kg_ha")
        )

        if curve["N_kg_ha"].nunique() < 2:
            continue

        max_yield = float(curve["yield_kg_ha"].max())
        threshold_yield = (
            RELATIVE_YIELD_THRESHOLD_PCT / 100.0
        ) * max_yield

        eligible = curve[curve["yield_kg_ha"] >= threshold_yield].copy()
        if eligible.empty:
            continue

        selected = eligible.sort_values("N_kg_ha").iloc[0]
        target_n = float(selected["N_kg_ha"])
        target_y = float(selected["yield_kg_ha"])

        row = dict(
            zip(
                keys,
                key_vals if isinstance(key_vals, tuple) else (key_vals,),
            )
        )

        row.update({
            "n_tested_N_rates": int(curve["N_kg_ha"].nunique()),
            "minimum_tested_N_kg_ha": float(curve["N_kg_ha"].min()),
            "maximum_tested_N_kg_ha": float(curve["N_kg_ha"].max()),
            "maximum_observed_yield_kg_ha": max_yield,
            "relative_yield_threshold_pct": RELATIVE_YIELD_THRESHOLD_PCT,
            "yield_threshold_kg_ha": threshold_yield,
            "selected_N_rate_kg_ha": target_n,
            "yield_at_selected_N_rate_kg_ha": target_y,
            "relative_yield_to_observed_maximum_pct": (
                100.0 * target_y / max_yield if max_yield > 0 else np.nan
            ),
            "N_rate_adjustment_vs_government_reference_kg_ha": target_n - 120.0,
            "potential_mineral_N_reduction_vs_N120_kg_ha": max(
                0.0, 120.0 - target_n
            ),
            "additional_N_requirement_vs_N120_kg_ha": max(
                0.0, target_n - 120.0
            ),
            "N_rate_adjustment_direction": (
                "lower rate"
                if target_n < 120
                else "higher rate"
                if target_n > 120
                else "maintain N120"
            ),
        })

        rows.append(row)

    return pd.DataFrame(rows)


def build_summary(stage):
    group_cols = [
        "study",
        "year",
        "variety",
        "stage",
        "stage_name",
        "treatment_role",
    ]

    rows = []

    for key_vals, g in stage.groupby(group_cols, dropna=False):
        row = dict(
            zip(
                group_cols,
                key_vals if isinstance(key_vals, tuple) else (key_vals,),
            )
        )

        row["n_districts"] = g["adm1"].nunique()
        row["n_sites"] = g["site"].nunique()
        row["n_records"] = len(g)

        yy = num(g["mean_yield_kg_ha"])
        row["mean_yield_kg_ha"] = yy.mean()
        row["median_yield_kg_ha"] = yy.median()
        row["sd_yield_kg_ha"] = yy.std()
        row["minimum_yield_kg_ha"] = yy.min()
        row["maximum_yield_kg_ha"] = yy.max()

        row["mean_N_rate_kg_ha"] = num(g["N_kg_ha"]).mean()
        row["mean_AE_N_kg_grain_per_kg_N"] = num(
            g["AE_N_kg_grain_per_kg_N"]
        ).mean()
        row["mean_PFP_N_kg_grain_per_kg_N"] = num(
            g["PFP_N_kg_grain_per_kg_N"]
        ).mean()

        matched = g[g["government_reference_available"]]
        row["n_sites_with_government_reference"] = matched["site"].nunique()
        row["mean_relative_yield_to_government_reference_pct"] = num(
            matched["relative_yield_to_government_reference_pct"]
        ).mean()

        applicable = g[g["potential_mineral_N_reduction_applicable"]]
        row["n_sites_with_lower_N_alternative"] = applicable["site"].nunique()

        if len(applicable):
            row["share_sites_ge_95pct_relative_yield"] = (
                num(
                    applicable[
                        "relative_yield_to_government_reference_pct"
                    ]
                )
                .ge(RELATIVE_YIELD_THRESHOLD_PCT)
                .mean()
            )
            row["mean_potential_mineral_N_reduction_kg_ha"] = num(
                applicable["potential_mineral_N_reduction_kg_ha"]
            ).mean()
        else:
            row["share_sites_ge_95pct_relative_yield"] = np.nan
            row["mean_potential_mineral_N_reduction_kg_ha"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows).sort_values(
        ["year", "study", "variety", "stage", "treatment_role"]
    )


def build_availability_matrix(stage):
    keys = ["study", "year", "variety"]

    base = (
        stage.groupby(keys, as_index=False, dropna=False)
        .agg(n_sites=("site", "nunique"))
    )

    for s in range(1, 7):
        x = (
            stage[stage["stage"].eq(s)]
            .groupby(keys, as_index=False, dropna=False)
            .agg(**{f"stage{s}_n_sites": ("site", "nunique")})
        )
        base = base.merge(x, on=keys, how="left")
        base[f"stage{s}_n_sites"] = (
            base[f"stage{s}_n_sites"].fillna(0).astype(int)
        )
        base[f"stage{s}_available"] = base[f"stage{s}_n_sites"] > 0

    return base.sort_values(["year", "study", "variety"])


def build_qc(df, stage):
    rows = []

    balanced_pk = (
        close_to(df["P2O5_kg_ha"], 60)
        & close_to(df["K2O_kg_ha"], 40)
        & df["N_kg_ha"].isin([0, 60, 78, 120, 180, 210])
    )

    unclassified = df[balanced_pk & df["stage"].isna()].copy()

    for _, r in unclassified.iterrows():
        rows.append({
            "qc_type": "unclassified_balanced_PK_treatment",
            "year": r["year"],
            "source_dataset": r["source_datasets"],
            "study": r["study"],
            "site": r["site"],
            "treatment_code": r["treatment_code"],
            "treatment": r["treatment"],
            "N_kg_ha": r["N_kg_ha"],
        })

    for (study, year, variety), g in stage.groupby(
        ["study", "year", "variety"],
        dropna=False,
    ):
        rows.append({
            "qc_type": "government_reference_coverage",
            "year": year,
            "source_dataset": ";".join(
                sorted(g["source_datasets"].dropna().astype(str).unique())
            ),
            "study": study,
            "site": None,
            "treatment_code": None,
            "treatment": variety,
            "N_kg_ha": None,
            "n_sites_total": g["site"].nunique(),
            "n_sites_with_government_reference": (
                g.loc[g["government_reference"], "site"].nunique()
            ),
        })

    return pd.DataFrame(rows)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing input:\n{INPUT}\n\n"
            "Run first:\n"
            "python .\\scripts\\0c_nsaf_data_legacy.py"
        )

    required = {
        "year",
        "adm1",
        "adm2",
        "site",
        "treatment_code",
        "treatment",
        "mean_yield_kg_ha",
        "mean_N_fertilizer_kg_ha",
        "mean_P2O5_fertilizer_kg_ha",
        "mean_K2O_fertilizer_kg_ha",
        "mean_organic_fertilizer_t_ha",
        "source_datasets",
    }

    raw = pd.read_csv(INPUT)

    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")

    df = initialise(raw)

    classify_2017(df)
    classify_2018(df)
    classify_2019(df)

    stage = df[df["stage"].notna()].copy()
    stage["stage"] = stage["stage"].astype(int)

    stage = add_agronomic_metrics(stage)

    n_rate_target = build_stage5_n_rate_targets(stage)
    summary = build_summary(stage)
    matrix = build_availability_matrix(stage)
    qc = build_qc(df, stage)

    stage = stage.sort_values([
        "year",
        "study",
        "variety",
        "adm1",
        "adm2",
        "site",
        "stage",
        "N_kg_ha",
    ])

    stage.to_csv(OUT_SITE, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    n_rate_target.to_csv(OUT_TARGET, index=False)
    matrix.to_csv(OUT_MATRIX, index=False)
    qc.to_csv(OUT_QC, index=False)

    print("\n" + "=" * 112)
    print("NSAF MAIZE STAGE 1-6 AGRONOMIC DESCRIPTIVES")
    print("=" * 112)
    print(f"Input rows:      {len(df):,}")
    print(f"Stage rows:      {len(stage):,}")
    print(f"Years:           {sorted(stage['year'].dropna().unique().tolist())}")
    print(f"Study blocks:    {stage['study'].nunique()}")
    print(f"Unique sites:    {stage['site'].nunique()}")
    print(
        "Relative-yield threshold for lower-N screening: "
        f"{RELATIVE_YIELD_THRESHOLD_PCT:.0f}%"
    )

    show = [
        "year",
        "study",
        "variety",
        "stage",
        "stage_name",
        "treatment_role",
        "n_sites",
        "mean_yield_kg_ha",
        "mean_N_rate_kg_ha",
        "mean_AE_N_kg_grain_per_kg_N",
        "mean_PFP_N_kg_grain_per_kg_N",
        "mean_relative_yield_to_government_reference_pct",
        "mean_potential_mineral_N_reduction_kg_ha",
    ]

    print("\n" + summary[show].to_string(index=False))

    if not n_rate_target.empty:
        print("\nSTAGE 5: N-RATE ADJUSTMENT")
        print("-" * 112)

        target_summary = (
            n_rate_target.groupby(
                [
                    "study",
                    "year",
                    "variety",
                    "N_rate_adjustment_direction",
                ],
                as_index=False,
                dropna=False,
            )
            .agg(
                n_sites=("site", "nunique"),
                mean_selected_N_rate_kg_ha=(
                    "selected_N_rate_kg_ha",
                    "mean",
                ),
                mean_potential_mineral_N_reduction_kg_ha=(
                    "potential_mineral_N_reduction_vs_N120_kg_ha",
                    "mean",
                ),
                mean_additional_N_requirement_kg_ha=(
                    "additional_N_requirement_vs_N120_kg_ha",
                    "mean",
                ),
            )
        )

        print(target_summary.to_string(index=False))

    print("\nOutputs:")
    for p in [OUT_SITE, OUT_SUMMARY, OUT_TARGET, OUT_MATRIX, OUT_QC]:
        print(f"  {p}")

    print("\nAgronomic interpretation:")
    print("  Relative yield (%) = treatment yield / government-reference yield x 100.")
    print("  AE-N uses the N0-P60-K40 reference.")
    print("  PFP-N is not calculated for FYM treatments because organic N is not quantified.")
    print(
        "  Potential mineral-N reduction is reported only for lower-N treatments "
        f"with >= {RELATIVE_YIELD_THRESHOLD_PCT:.0f}% relative yield."
    )
    print(
        "  Stage 5 uses the lowest tested N rate achieving >=95% relative yield "
        "to the maximum observed yield in the tested N-rate response."
    )
    print("  No DSM extrapolation or crop-area scaling is applied.")


if __name__ == "__main__":
    main()
