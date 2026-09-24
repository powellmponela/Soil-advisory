import pandas as pd
from _project_paths import DATA_DIR

# File Paths
DSM_FILE = DATA_DIR / "dsm_western_terai_midhill_pixel-centroid.csv"
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
PROCESSED_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"

def check_pixel_coverage():
    # 1. Load All Trial Sites
    df17 = pd.read_excel(TRIAL_2017)
    df18 = pd.read_csv(TRIAL_2018)
    df19 = pd.read_csv(PROCESSED_2019)
    sites19 = df19[['lat_fixed', 'lon_fixed']].rename(
        columns={'lat_fixed': 'latitude', 'lon_fixed': 'longitude'}
    ).dropna()
    
    all_sites = pd.concat([
        df17[['latitude', 'longitude']].dropna(),
        df18[['latitude', 'longitude']].dropna(),
        sites19
    ], ignore_index=True)
    
    # 2. Load DSM Grid
    dsm = pd.read_csv(DSM_FILE)
    dsm_pixels = set(zip(dsm['lat'].round(4), dsm['lon'].round(4)))
    
    # 3. Map Trial Sites to 0.02 Pixels
    # A 0.02 grid usually has centroids at multiples of 0.02 (e.g. 27.50, 27.52, ...)
    # We round trial lat/lon to nearest 0.02
    all_sites['pixel_lat'] = (all_sites['latitude'] / 0.02).round() * 0.02
    all_sites['pixel_lon'] = (all_sites['longitude'] / 0.02).round() * 0.02
    
    # Distinct pixels occupied by trial sites
    trial_pixels = all_sites[['pixel_lat', 'pixel_lon']].drop_duplicates()
    trial_pixels['pixel_lat'] = trial_pixels['pixel_lat'].round(4)
    trial_pixels['pixel_lon'] = trial_pixels['pixel_lon'].round(4)
    
    print(f"Distinct 0.02-degree Pixels occupied by 702 trial sites: {len(trial_pixels)}")
    
    # 4. Check overlap with our extracted DSM
    overlap = trial_pixels[trial_pixels.apply(lambda x: (x.pixel_lat, x.pixel_lon) in dsm_pixels, axis=1)]
    print(f"Trial pixels already present in our DSM extraction: {len(overlap)}")
    
    # Which districts are covered?
    # We'll merge with the DSM to see districts
    coverage_details = overlap.merge(dsm[['lat', 'lon', 'district']], left_on=['pixel_lat', 'pixel_lon'], right_on=['lat', 'lon'])
    print("\nCoverage by District (Distinct Pixels):")
    print(coverage_details['district'].value_counts())

if __name__ == "__main__":
    check_pixel_coverage()
