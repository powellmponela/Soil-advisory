from pathlib import Path
import numpy as np
import pandas as pd
from importlib.machinery import SourceFileLoader

C = SourceFileLoader("common", str(Path(__file__).with_name("00_common.py"))).load_module()

ALTERNATIVES = [
    "TIMING_V6V10", "TIMING_V8",
    "ZN_SUPPORT", "KS_SUPPORT",
    "UDP_N78", "UDP_N120",
    "PCU_N60", "PCU_N120",
]

def main():
    args = C.parser_for("Stage 6: efficiency alternatives around the N target").parse_args()
    long = C.load_long(args.workbook)

    gov = long[long["treatment_class"] == "GOVT_N120"][
        ["trial_year_id", "yield_kg_ha", "N_kg_ha"]
    ].rename(columns={
        "yield_kg_ha": "govt_yield_kg_ha",
        "N_kg_ha": "govt_N_kg_ha"
    })

    n0 = long[long["treatment_class"] == "N0_PK"][
        ["trial_year_id", "yield_kg_ha"]
    ].rename(columns={"yield_kg_ha": "yield_0PK_kg_ha"})

    alt = long[long["treatment_class"].isin(ALTERNATIVES)].copy()
    alt = alt.merge(gov, on="trial_year_id", how="inner").merge(n0, on="trial_year_id", how="left")
    alt = alt.rename(columns={
        "treatment_class": "alternative",
        "yield_kg_ha": "alternative_yield_kg_ha",
        "N_kg_ha": "alternative_N_kg_ha"
    })

    alt["yield_difference_vs_govt_kg_ha"] = alt["alternative_yield_kg_ha"] - alt["govt_yield_kg_ha"]
    alt["yield_retention_vs_govt"] = C.retention(
        alt["alternative_yield_kg_ha"], alt["govt_yield_kg_ha"]
    )
    alt["N_difference_vs_govt_kg_ha"] = alt["alternative_N_kg_ha"] - alt["govt_N_kg_ha"]
    alt["candidate_N_reduction_kg_ha"] = np.maximum(
        0.0, alt["govt_N_kg_ha"] - alt["alternative_N_kg_ha"]
    )
    alt["estimated_N_saving_if_retained_kg_ha"] = np.where(
        (alt["candidate_N_reduction_kg_ha"] > 0) &
        (alt["yield_retention_vs_govt"] >= args.retention),
        alt["candidate_N_reduction_kg_ha"],
        0.0
    )

    alt["PFP_N_alt_kg_grain_per_kg_N"] = np.where(
        alt["alternative_N_kg_ha"] > 0,
        alt["alternative_yield_kg_ha"] / alt["alternative_N_kg_ha"],
        np.nan
    )
    alt["PFP_N_govt_kg_grain_per_kg_N"] = alt["govt_yield_kg_ha"] / alt["govt_N_kg_ha"]
    alt["delta_PFP_N_vs_govt"] = (
        alt["PFP_N_alt_kg_grain_per_kg_N"] - alt["PFP_N_govt_kg_grain_per_kg_N"]
    )

    # AE-N relative to N0-P-K when the same N-response baseline exists.
    alt["AE_N_alt_kg_grain_per_kg_N"] = np.where(
        alt["alternative_N_kg_ha"] > 0,
        (alt["alternative_yield_kg_ha"] - alt["yield_0PK_kg_ha"]) / alt["alternative_N_kg_ha"],
        np.nan
    )
    alt["AE_N_govt_kg_grain_per_kg_N"] = (
        (alt["govt_yield_kg_ha"] - alt["yield_0PK_kg_ha"]) / alt["govt_N_kg_ha"]
    )
    alt["delta_AE_N_vs_govt"] = alt["AE_N_alt_kg_grain_per_kg_N"] - alt["AE_N_govt_kg_grain_per_kg_N"]

    # FYM is intentionally excluded here because it is handled as Stage 3 farmer-practice proxy.
    # "N saving" here means reduced mineral-N input with retained yield; it is NOT measured N loss reduction.
    C.write_stage_outputs(
        alt, Path(args.out) / "stage6_efficiency_alternatives",
        "stage6_efficiency_alternatives",
        ["alternative_yield_kg_ha", "yield_difference_vs_govt_kg_ha",
         "yield_retention_vs_govt", "alternative_N_kg_ha",
         "candidate_N_reduction_kg_ha", "estimated_N_saving_if_retained_kg_ha",
         "PFP_N_alt_kg_grain_per_kg_N", "delta_PFP_N_vs_govt",
         "AE_N_alt_kg_grain_per_kg_N", "delta_AE_N_vs_govt"]
    )

    # Alternative-specific summaries are useful for mapping and interpretation.
    out = Path(args.out) / "stage6_efficiency_alternatives"
    rows = []
    for (study, year, district, alternative), g in alt.groupby(
        ["study", "year", "district", "alternative"], dropna=False
    ):
        rows.append({
            "study": study,
            "year": year,
            "district": district,
            "alternative": alternative,
            "n_trial_years": g["trial_year_id"].nunique(),
            "n_sites": g["site"].nunique() if "site" in g.columns else np.nan,
            "mean_yield_retention": g["yield_retention_vs_govt"].mean(),
            "mean_yield_difference_kg_ha": g["yield_difference_vs_govt_kg_ha"].mean(),
            "mean_N_saving_if_retained_kg_ha": g["estimated_N_saving_if_retained_kg_ha"].mean(),
            "share_retaining_threshold": (g["yield_retention_vs_govt"] >= args.retention).mean(),
            "mean_delta_AE_N": g["delta_AE_N_vs_govt"].mean(),
        })
    pd.DataFrame(rows).to_csv(
        out / "stage6_by_alternative_study_year_district.csv", index=False
    )

if __name__ == "__main__":
    main()
