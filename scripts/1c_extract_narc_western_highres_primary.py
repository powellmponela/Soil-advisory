from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(r"D:\dss\SOIL ADVISORY")
DATA_DIR = ROOT / "Data"
OUTPUT_FILE = DATA_DIR / "dsm_western_terai_midhill_pixel-centroid.csv"
API_URL = "https://soil.narc.gov.np/soil/api/soildata"

WESTERN_PROVINCES = {
    "Province 5", "Province 6", "Province 7",
    "Lumbini", "Karnali", "Sudurpashchim", "5", "6", "7"
}

# Full deterministic grid. Do not truncate to the first 5,000 points.
LON_RANGE = np.arange(80.0, 84.6, 0.02)
LAT_RANGE_TERAI = np.arange(27.5, 28.0, 0.02)
LAT_RANGE_HILLS = np.arange(28.0, 28.6, 0.02)
GRID_POINTS = [
    (round(lat, 4), round(lon, 4))
    for lat in np.concatenate([LAT_RANGE_TERAI, LAT_RANGE_HILLS])
    for lon in LON_RANGE
]

DSM_COLS = [
    "ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg",
    "sand_pct", "clay_pct", "silt_pct"
]


def clean_value(val):
    if val is None or val == "NA":
        return None
    m = re.search(r"[-+]?\d*\.\d+|\d+", re.sub("<[^<]+?>", "", str(val)))
    return float(m.group()) if m else None


def nz(val):
    x = clean_value(val)
    return 0.0 if x is None else x


def get_session():
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=30, pool_maxsize=30)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_point(lat, lon):
    session = get_session()
    try:
        r = session.get(API_URL, params={"lat": lat, "lon": lon}, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
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
            "maize_urea_total": nz(maize_rec.get("UREA1")) + nz(maize_rec.get("UREA2")) + nz(maize_rec.get("UREA3")),
            "maize_dap": clean_value(maize_rec.get("DAP")),
            "maize_mop": clean_value(maize_rec.get("MOP")),
            "dsm_source": "NARC_API_modelled_DSM",
        }
    except (requests.RequestException, ValueError, TypeError):
        return None


def fill_missing_dsm_from_nearest8(df, k=8, min_neighbors=3):
    out = df.copy()
    out["dsm_imputed"] = False
    out["dsm_imputation_n_neighbors"] = 0
    lat = out["lat"].astype(float).to_numpy()
    lon = out["lon"].astype(float).to_numpy()
    mean_lat_rad = np.deg2rad(np.nanmean(lat))
    x = lon * 111_320.0 * np.cos(mean_lat_rad)
    y = lat * 110_540.0

    for col in DSM_COLS:
        valid = out[col].notna().to_numpy()
        missing = out[col].isna().to_numpy()
        if valid.sum() < min_neighbors or not missing.any():
            continue
        valid_idx = np.where(valid)[0]
        vals = out.iloc[valid_idx][col].astype(float).to_numpy()
        for idx in np.where(missing)[0]:
            dist = np.sqrt((x[valid_idx] - x[idx])**2 + (y[valid_idx] - y[idx])**2)
            sel = np.argsort(dist)[:min(k, len(dist))]
            v = vals[sel]
            v = v[~np.isnan(v)]
            if len(v) >= min_neighbors:
                out.at[idx, col] = float(np.mean(v))
                out.at[idx, "dsm_imputed"] = True
                out.at[idx, "dsm_imputation_n_neighbors"] = max(int(out.at[idx, "dsm_imputation_n_neighbors"]), len(v))

    out["dsm_imputation_method"] = np.where(out["dsm_imputed"], "nearest_8_valid_mean", "none")
    return out


def main():
    print(f"Querying {len(GRID_POINTS)} grid points for western Terai and mid-hills...")
    rows = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_point, lat, lon): (lat, lon) for lat, lon in GRID_POINTS}
        for i, fut in enumerate(as_completed(futures), 1):
            row = fut.result()
            if row is not None:
                rows.append(row)
            if i % 1000 == 0:
                print(f"Processed {i}/{len(GRID_POINTS)}; retained {len(rows)} western pixels")

    if not rows:
        raise RuntimeError("No western Nepal DSM records returned.")

    df = pd.DataFrame(rows).sort_values(["district", "lat", "lon"]).reset_index(drop=True)
    df = fill_missing_dsm_from_nearest8(df)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} pixels to {OUTPUT_FILE}")
    print(f"Pixels with DSM gap filling: {int(df['dsm_imputed'].sum())}")


if __name__ == "__main__":
    main()
