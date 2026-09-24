import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from _project_paths import DATA_DIR

# Configuration
OUTPUT_FILE = DATA_DIR / "narc_baseline_maize_pixel_western.csv"
API_URL = "https://soil.narc.gov.np/soil/api/soildata"
WESTERN_PROVINCES = {
    "Province 5",
    "Province 6",
    "Province 7",
    "Lumbini",
    "Karnali",
    "Sudurpashchim",
    "5",
    "6",
    "7",
}

# Bounding box for Western Nepal
LON_RANGE = np.arange(80.0, 84.6, 0.05)
LAT_RANGE = np.arange(27.5, 30.1, 0.05)
GRID_POINTS = [(round(lat, 3), round(lon, 3)) for lat in LAT_RANGE for lon in LON_RANGE]


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



def get_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def clean_value(val):
    if val is None or val == "NA":
        return None
    clean_text = re.sub("<[^<]+?>", "", str(val))
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean_text)
    if match:
        return float(match.group())
    return None


def nz(val):
    return clean_value(val) or 0.0


def fetch_point(session, lat, lon):
    params = {"lat": lat, "lon": lon}
    try:
        response = session.get(API_URL, params=params, timeout=15)
        if response.status_code != 200:
            return None

        data = response.json()
        province = data.get("province")
        if province not in WESTERN_PROVINCES:
            return None

        maize_rec = data.get("fertilizerData", {}).get("Maize", {}).get("Hybrid", {})
        if not maize_rec:
            maize_rec = data.get("fertilizerData", {}).get("Maize", {}).get("OPV", {})

        return {
            "province": province,
            "district": data.get("district"),
            "palika": data.get("palika"),
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
            "maize_urea_total": nz(maize_rec.get("UREA1"))
            + nz(maize_rec.get("UREA2"))
            + nz(maize_rec.get("UREA3")),
            "maize_dap": clean_value(maize_rec.get("DAP")),
            "maize_mop": clean_value(maize_rec.get("MOP")),
            "dsm_source": "direct_overlay",
        }
    except (requests.RequestException, ValueError):
        return None


def fetch_regional_data_parallel():
    results = []
    session = get_session()
    print(f"Starting parallel Western extraction for {len(GRID_POINTS)} points...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_point, session, lat, lon): (lat, lon)
            for lat, lon in GRID_POINTS
        }

        found_count = 0
        for count, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            if res:
                results.append(res)
                found_count += 1

            if count % 100 == 0:
                print(f"Progress: {count}/{len(GRID_POINTS)} (Found {found_count} pixels)")

    return pd.DataFrame(results)


if __name__ == "__main__":
    baseline_data = fetch_regional_data_parallel()
    if not baseline_data.empty:
        baseline_data = fill_missing_dsm_from_nearest8(
            baseline_data,
            lat_col="lat",
            lon_col="lon",
            dsm_cols=available_dsm_cols(baseline_data),
        )
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        baseline_data.to_csv(OUTPUT_FILE, index=False)
        n_imputed = int(baseline_data["dsm_imputed"].sum())
        print(f"\nSuccessfully saved {len(baseline_data)} Western pixels to {OUTPUT_FILE}")
        print(f"DSM nearest-8 gap-filled pixels: {n_imputed}")
    else:
        print("No data fetched.")
