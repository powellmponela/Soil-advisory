import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from _project_paths import DATA_DIR

# Configuration
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
DEMO_2019 = MAIZE_DIR / "maize_demo_2019.xlsx"
OUTPUT_SOIL_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"
OUTPUT_CONTROLS = DATA_DIR / "nsaf_pooled_controls_2017_2019.csv"
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



def extract_coords(row):
    """Extract and validate latitude/longitude from the combined ODK GPS field."""
    try:
        values = re.findall(r"[-+]?\d+(?:\.\d+)?", str(row["latitude"]))
        if len(values) >= 2:
            lat, lon = float(values[0]), float(values[1])
            if 26.0 <= lat <= 31.0 and 80.0 <= lon <= 89.0:
                return lat, lon
    except (KeyError, TypeError, ValueError):
        pass
    return None, None


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
            "lat_key": lat,
            "lon_key": lon,
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
    df17 = pd.read_excel(TRIAL_2017)
    df18 = pd.read_csv(TRIAL_2018)
    df19 = pd.read_excel(DEMO_2019)

    df19["lat_fixed"], df19["lon_fixed"] = zip(*df19.apply(extract_coords, axis=1))

    c17 = df17[(df17.N_kg_ha == 0) & (df17.P2O5_kg_ha == 0) & (df17.K2O_kg_ha == 0)][
        ["District", "Yield_t_ha"]
    ]
    c18 = df18[(df18.N_kg_ha == 0) & (df18.P2O5_kg_ha == 0) & (df18.K2O_kg_ha == 0)][
        ["District", "Yield_t_ha"]
    ]
    c19 = df19[(df19.N_kg_ha == 0) & (df19.P2O5_kg_ha == 0) & (df19.K2O_kg_ha == 0)][
        ["District", "Yield_t_ha"]
    ]

    os.makedirs(os.path.dirname(OUTPUT_CONTROLS), exist_ok=True)
    pooled_controls = pd.concat([c17, c18, c19], ignore_index=True)
    pooled_controls.to_csv(OUTPUT_CONTROLS, index=False)
    print(f"Pooled {len(pooled_controls)} control records.")

    plots19 = df19[["lat_fixed", "lon_fixed"]].dropna().drop_duplicates()
    print(f"Fetching NARC soil data for {len(plots19)} plots from 2019...")

    results = []
    session = requests.Session()
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(fetch_point, session, lat, lon): (lat, lon)
            for lat, lon in plots19.itertuples(index=False)
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    df_soil19 = pd.DataFrame(results)
    plots_soil19 = plots19.rename(columns={"lat_fixed": "lat_key", "lon_fixed": "lon_key"})
    if not df_soil19.empty:
        plots_soil19 = plots_soil19.merge(df_soil19, on=["lat_key", "lon_key"], how="left")
    else:
        for col in DSM_COLS + ["narc_dist", "dsm_source"]:
            plots_soil19[col] = np.nan
        plots_soil19["dsm_source"] = "api_no_match"

    plots_soil19["dsm_source"] = plots_soil19["dsm_source"].fillna("api_no_match")
    plots_soil19 = fill_missing_dsm_from_nearest8(
        plots_soil19,
        lat_col="lat_key",
        lon_col="lon_key",
        dsm_cols=available_dsm_cols(plots_soil19),
    )

    df_final19 = df19.merge(
        plots_soil19,
        left_on=["lat_fixed", "lon_fixed"],
        right_on=["lat_key", "lon_key"],
        how="left",
    )
    os.makedirs(os.path.dirname(OUTPUT_SOIL_2019), exist_ok=True)
    df_final19.to_csv(OUTPUT_SOIL_2019, index=False)

    n_direct = int((plots_soil19["dsm_source"] == "direct_overlay").sum())
    n_imputed = int(plots_soil19["dsm_imputed"].sum())
    print(f"Matched/saved {len(df_final19)} records for 2019.")
    print(f"Direct DSM plot matches: {n_direct}; nearest-8 imputed plots: {n_imputed}")
