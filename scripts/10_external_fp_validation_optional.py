"""Optional external validation against household-survey farmer practice data."""

from pathlib import Path

import pandas as pd
from scipy.spatial import cKDTree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

SURVEY_FILE = (
    DATA_DIR / "HH Survey" / "survey_crop_cut_data_merged_07_Aug-2024.xlsx"
)
TRIAL_FILE = OUTPUT_ROOT / "merged_maize_trials_carob_like.csv"
OUTPUT_FILE = OUTPUT_ROOT / "external_fp_validation_results.csv"
MAX_DISTANCE_DEGREES = 0.5


def calculate_nitrogen(urea: pd.Series, dap: pd.Series) -> pd.Series:
    """Calculate applied N from urea (46% N) and DAP (18% N)."""
    return (urea * 0.46) + (dap * 0.18)


def run_external_check() -> None:
    """Match farmer-practice observations to their nearest trial locations."""
    if not SURVEY_FILE.exists() or not TRIAL_FILE.exists():
        print(f"Missing required files: {SURVEY_FILE} or {TRIAL_FILE}")
        return

    # copy() consolidates the wide Excel frame before adding derived columns.
    survey_df = pd.read_excel(SURVEY_FILE).rename(
        columns={"Latitude ": "lat", "Longitude": "lon"}
    ).copy()

    final_yield = (
        survey_df["CC_yield_t_ha"]
        .fillna(survey_df["yield_t_ha_this_yr"])
        .fillna(survey_df["S_yield_t_ha"])
    )
    survey_df = pd.concat(
        [survey_df, final_yield.rename("final_yield")], axis=1, copy=False
    )
    survey_df = survey_df.dropna(subset=["lat", "lon", "final_yield"]).copy()
    print(f"Total survey records with GPS and Yield: {len(survey_df)}")

    applied_n = calculate_nitrogen(
        survey_df["urea_this_yr_kg"].fillna(0),
        survey_df["dap_this_yr_kg_ha"].fillna(0),
    )
    survey_df = pd.concat(
        [survey_df, applied_n.rename("N_applied_kg_ha")], axis=1, copy=False
    )

    trial_df = (
        pd.read_csv(TRIAL_FILE)
        .rename(columns={"latitude": "lat", "longitude": "lon"})
        .dropna(subset=["lat", "lon"])
        .copy()
    )
    print(f"Total trial records with GPS: {len(trial_df)}")

    tree = cKDTree(trial_df[["lat", "lon"]].to_numpy())
    distance, nearest_index = tree.query(survey_df[["lat", "lon"]].to_numpy())
    nearest_trials = trial_df.iloc[nearest_index]

    match_columns = pd.DataFrame(
        {
            "nearest_trial_yield": nearest_trials["yield_t_ha"].to_numpy(),
            "nearest_trial_N": nearest_trials["N_fertilizer_kg_ha"].to_numpy(),
            "spatial_dist_deg": distance,
        },
        index=survey_df.index,
    )
    survey_df = pd.concat([survey_df, match_columns], axis=1, copy=False)

    validation = survey_df.loc[
        survey_df["spatial_dist_deg"] < MAX_DISTANCE_DEGREES
    ].copy()
    if validation.empty:
        print(f"No records found within {MAX_DISTANCE_DEGREES} degrees.")
        return

    summary = {
        "count": len(validation),
        "avg_fp_yield": validation["final_yield"].mean(),
        "avg_trial_yield": validation["nearest_trial_yield"].mean(),
        "avg_fp_n": validation["N_applied_kg_ha"].mean(),
        "avg_trial_n": validation["nearest_trial_N"].mean(),
        "yield_gap_fp_trial": (
            validation["nearest_trial_yield"].mean()
            - validation["final_yield"].mean()
        ),
    }

    print(
        "\n--- EXTERNAL FARMER PRACTICE VALIDATION "
        f"(Limit: {MAX_DISTANCE_DEGREES} deg) ---"
    )
    print(f"Matched Records: {summary['count']}")
    print(f"Avg Farmer Yield (Survey/CC): {summary['avg_fp_yield']:.2f} t/ha")
    print(f"Avg Nearest Trial Yield: {summary['avg_trial_yield']:.2f} t/ha")
    print(f"Avg Farmer N-Applied: {summary['avg_fp_n']:.2f} kg/ha")
    print(f"Avg Nearest Trial N-Applied: {summary['avg_trial_n']:.2f} kg/ha")
    print(f"Yield Gap (Trial - FP): {summary['yield_gap_fp_trial']:.2f} t/ha")

    validation = validation.drop(
        columns=[column for column in ["fmr_nm", "cntct_no"] if column in validation],
    )
    if "_id" in validation.columns:
        validation = validation.rename(columns={"_id": "farmer_id"})

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    validation.to_csv(OUTPUT_FILE, index=False)
    print(f"Validation results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_external_check()
