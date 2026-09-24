import os
import re
import time

import numpy as np
import pandas as pd
import requests
from _project_paths import DATA_DIR

# Configuration
OUTPUT_FILE = DATA_DIR / "narc_baseline_maize.csv"
API_URL = "https://soil.narc.gov.np/soil/api/soildata"

# Representative coordinates for Eastern Nepal regions
REPRESENTATIVE_COORDS = [
    {"dist": "Jhapa", "lat": 26.635, "lon": 87.985},
    {"dist": "Jhapa", "lat": 26.560, "lon": 87.720},
    {"dist": "Jhapa", "lat": 26.672, "lon": 87.684},
    {"dist": "Jhapa", "lat": 26.549, "lon": 88.089},
    {"dist": "Jhapa", "lat": 26.673, "lon": 87.973},
    {"dist": "Morang", "lat": 26.485, "lon": 87.285},
    {"dist": "Morang", "lat": 26.666, "lon": 87.592},
    {"dist": "Morang", "lat": 26.658, "lon": 87.410},
    {"dist": "Morang", "lat": 26.655, "lon": 87.545},
    {"dist": "Morang", "lat": 26.745, "lon": 87.497},
    {"dist": "Sunsari", "lat": 26.665, "lon": 87.272},
    {"dist": "Sunsari", "lat": 26.790, "lon": 87.290},
    {"dist": "Sunsari", "lat": 26.603, "lon": 87.148},
    {"dist": "Sunsari", "lat": 26.573, "lon": 87.274},
    {"dist": "Sunsari", "lat": 26.653, "lon": 87.171},
    {"dist": "Saptari", "lat": 26.542, "lon": 86.757},
    {"dist": "Saptari", "lat": 26.638, "lon": 86.912},
    {"dist": "Saptari", "lat": 26.611, "lon": 86.681},
    {"dist": "Saptari", "lat": 26.615, "lon": 86.765},
    {"dist": "Saptari", "lat": 26.621, "lon": 86.519},
    {"dist": "Dhankuta", "lat": 26.983, "lon": 87.333},
    {"dist": "Dhankuta", "lat": 27.049, "lon": 87.294},
    {"dist": "Dhankuta", "lat": 27.144, "lon": 87.274},
    {"dist": "Dhankuta", "lat": 27.025, "lon": 87.241},
    {"dist": "Dhankuta", "lat": 26.960, "lon": 87.230},
    {"dist": "Ilam", "lat": 26.911, "lon": 87.924},
    {"dist": "Ilam", "lat": 26.857, "lon": 88.087},
    {"dist": "Ilam", "lat": 26.897, "lon": 88.071},
    {"dist": "Ilam", "lat": 26.946, "lon": 88.115},
    {"dist": "Ilam", "lat": 26.903, "lon": 87.732},
    {"dist": "Panchthar", "lat": 27.152, "lon": 87.761},
    {"dist": "Panchthar", "lat": 27.051, "lon": 87.625},
    {"dist": "Panchthar", "lat": 26.930, "lon": 87.670},
    {"dist": "Panchthar", "lat": 27.266, "lon": 87.730},
    {"dist": "Panchthar", "lat": 26.883, "lon": 87.609},
]


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
    """Extract a numeric value from NARC HTML/string values."""
    if val is None or val == "NA":
        return None
    clean_text = re.sub("<[^<]+?>", "", str(val))
    match = re.search(r"[-+]?\d*\.\d+|\d+", clean_text)
    if match:
        return float(match.group())
    return None


def nz(val):
    return clean_value(val) or 0.0


def empty_row(item, source):
    return {
        "district_requested": item["dist"],
        "district_actual": None,
        "lat": item["lat"],
        "lon": item["lon"],
        "ph": None,
        "om_pct": None,
        "n_total_pct": None,
        "p_olsen_mg_kg": None,
        "k_exch_mg_kg": None,
        "sand_pct": None,
        "clay_pct": None,
        "silt_pct": None,
        "maize_urea_total": None,
        "maize_dap": None,
        "maize_mop": None,
        "dsm_source": source,
    }


def fetch_narc_data(coords_list):
    """Fetch and clean soil and maize data from the NARC API."""
    results = []
    print(f"Fetching data from NARC API for {len(coords_list)} locations...")

    for item in coords_list:
        lat, lon, dist_req = item["lat"], item["lon"], item["dist"]
        params = {"lat": lat, "lon": lon}

        try:
            response = requests.get(API_URL, params=params, timeout=15)
            if response.status_code != 200:
                print(f"Error {response.status_code} for {lat}, {lon}")
                results.append(empty_row(item, "api_no_match"))
                time.sleep(0.5)
                continue

            data = response.json()
            maize_rec = data.get("fertilizerData", {}).get("Maize", {}).get("Hybrid", {})
            if not maize_rec:
                maize_rec = data.get("fertilizerData", {}).get("Maize", {}).get("OPV", {})

            flat_data = {
                "district_requested": dist_req,
                "district_actual": data.get("district"),
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
            results.append(flat_data)
            print(f"Fetched and cleaned data for {dist_req} ({lat}, {lon})")
            time.sleep(0.5)
        except (requests.RequestException, ValueError) as exc:
            print(f"Request failed for {lat}, {lon}: {exc}")
            results.append(empty_row(item, "api_failed"))

    return pd.DataFrame(results)


if __name__ == "__main__":
    baseline_data = fetch_narc_data(REPRESENTATIVE_COORDS)
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
        print(f"\nSaved {len(baseline_data)} records to {OUTPUT_FILE}")
        print(f"DSM nearest-8 gap-filled records: {n_imputed}")
    else:
        print("No data fetched from API.")
