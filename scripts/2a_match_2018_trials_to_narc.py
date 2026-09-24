import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from _project_paths import DATA_DIR

# Configuration
TRIAL_DATA = DATA_DIR / "NSAF Crops Trial Data" / "Maize" / "maize_trials-2018.csv"
OUTPUT_FILE = DATA_DIR / "nsaf_plots_narc_soil.csv"
API_URL = "https://soil.narc.gov.np/soil/api/soildata"


DSM_COLS = [
    "ph",
    "om_pct",
    "n_total_pct",
    "p_olsen_mg_kg",
    "k_exch_mg_kg",
    "sand_pct",
    "clay_pct",
    "silt_pct",
]


def available_dsm_cols(df):
    return [col for col in DSM_COLS if col in df.columns]


def fill_missing_dsm_from_nearest8(
    df,
    lat_col="lat",
    lon_col="lon",
    dsm_cols=None,
    k=8,
    min_neighbors=3,
):
    """Fill missing DSM covariates from the mean of the nearest valid neighbours.

    Only DSM covariates are imputed. Yield, treatment, fertilizer rates,
    farmer identifiers, and management variables are never changed.
    """
    if dsm_cols is None:
        dsm_cols = available_dsm_cols(df)

    out = df.copy()
    if "dsm_imputed" not in out.columns:
        out["dsm_imputed"] = False
    if "dsm_imputation_n_neighbors" not in out.columns:
        out["dsm_imputation_n_neighbors"] = 0
    if "dsm_source" not in out.columns:
        out["dsm_source"] = np.where(
            out[dsm_cols].notna().any(axis=1), "direct_overlay", "api_no_match"
        )
    out["dsm_imputation_method"] = np.where(
        out["dsm_imputed"], "nearest_8_valid_mean", out["dsm_source"]
    )

    if lat_col not in out.columns or lon_col not in out.columns:
        return out

    coord_mask = out[lat_col].notna() & out[lon_col].notna()
    if not coord_mask.any():
        return out

    lat = out[lat_col].astype(float).to_numpy()
    lon = out[lon_col].astype(float).to_numpy()
    # Approximate local planar distance in metres. Good enough for nearest
    # neighbour selection over Nepal at plot/pixel scales.
    mean_lat_rad = np.deg2rad(np.nanmean(lat))
    x = lon * 111_320.0 * np.cos(mean_lat_rad)
    y = lat * 110_540.0

    for col in dsm_cols:
        valid_mask = out[col].notna() & coord_mask
        missing_mask = out[col].isna() & coord_mask
        if valid_mask.sum() < min_neighbors or not missing_mask.any():
            continue

        valid_indices = np.where(valid_mask.to_numpy())[0]
        missing_indices = np.where(missing_mask.to_numpy())[0]
        valid_values = out.iloc[valid_indices][col].astype(float).to_numpy()

        for idx in missing_indices:
            dx = x[valid_indices] - x[idx]
            dy = y[valid_indices] - y[idx]
            distances = np.sqrt(dx * dx + dy * dy)
            nearest_order = np.argsort(distances)[: min(k, len(distances))]
            neighbour_values = valid_values[nearest_order]
            neighbour_values = neighbour_values[~np.isnan(neighbour_values)]

            if len(neighbour_values) >= min_neighbors:
                out.iat[idx, out.columns.get_loc(col)] = float(np.mean(neighbour_values))
                out.iat[idx, out.columns.get_loc("dsm_imputed")] = True
                current_n = out.iat[idx, out.columns.get_loc("dsm_imputation_n_neighbors")]
                out.iat[idx, out.columns.get_loc("dsm_imputation_n_neighbors")] = max(
                    int(current_n), len(neighbour_values)
                )

    out["dsm_source"] = np.where(
        out["dsm_imputed"] & (out["dsm_source"] == "direct_overlay"),
        "direct_overlay_plus_nearest8",
        np.where(out["dsm_imputed"], "nearest8_mean", out["dsm_source"]),
    )
    out["dsm_imputation_method"] = np.where(
        out["dsm_imputed"], "nearest_8_valid_mean", out["dsm_source"]
    )
    return out



def clean_value(val):
    if val is None or val == "NA":
        return None
    clean_text = re.sub("<[^<]+?>", "", str(val))
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean_text)
    if match:
        return float(match.group())
    return None


def fetch_point(session, lat, lon):
    params = {"lat": lat, "lon": lon}
    try:
        response = session.get(API_URL, params=params, timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        return {
            "lat": lat,
            "lon": lon,
            "ph": clean_value(data.get("ph")),
            "om_pct": clean_value(data.get("organic_matter")),
            "n_total_pct": clean_value(data.get("total_nitrogen")),
            "p_olsen_mg_kg": clean_value(data.get("p2o5")),
            "k_exch_mg_kg": clean_value(data.get("potassium")),
            "sand_pct": clean_value(data.get("sand")),
            "clay_pct": clean_value(data.get("clay")),
            "silt_pct": clean_value(data.get("slit")),
            "narc_dist": data.get("district"),
            "dsm_source": "direct_overlay",
        }
    except (requests.RequestException, ValueError):
        return None


if __name__ == "__main__":
    df_trials = pd.read_csv(TRIAL_DATA)
    plots = df_trials[["latitude", "longitude"]].dropna().drop_duplicates()
    print(f"Found {len(plots)} unique 2018 trial plot locations.")

    results = []
    session = requests.Session()
    print(f"Fetching NARC soil data for {len(plots)} plots...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_point, session, row.latitude, row.longitude): row
            for _, row in plots.iterrows()
        }

        for count, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            if res:
                results.append(res)
            if count % 20 == 0:
                print(f"Processed {count}/{len(plots)} locations...")

    df_soil = pd.DataFrame(results)
    plots_soil = plots.rename(columns={"latitude": "lat", "longitude": "lon"})
    if not df_soil.empty:
        plots_soil = plots_soil.merge(df_soil, on=["lat", "lon"], how="left")
    else:
        for col in DSM_COLS + ["narc_dist", "dsm_source"]:
            plots_soil[col] = np.nan
        plots_soil["dsm_source"] = "api_no_match"

    plots_soil["dsm_source"] = plots_soil["dsm_source"].fillna("api_no_match")
    plots_soil = fill_missing_dsm_from_nearest8(
        plots_soil,
        lat_col="lat",
        lon_col="lon",
        dsm_cols=available_dsm_cols(plots_soil),
    )

    df_final = df_trials.merge(
        plots_soil,
        left_on=["latitude", "longitude"],
        right_on=["lat", "lon"],
        how="left",
    )

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False)
    n_direct = int((plots_soil["dsm_source"] == "direct_overlay").sum())
    n_imputed = int(plots_soil["dsm_imputed"].sum())
    print(f"\nSaved {len(df_final)} 2018 records with DSM covariates.")
    print(f"Direct DSM plot matches: {n_direct}; nearest-8 imputed plots: {n_imputed}")
    print(f"Saved to {OUTPUT_FILE}")
