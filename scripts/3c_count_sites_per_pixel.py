import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
PROCESSED_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"

def count_sites_per_pixel():
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
    
    # 2. Get Distinct GPS Locations
    distinct_gps = all_sites.drop_duplicates().copy()
    
    # 3. Map to 0.02-degree pixels
    distinct_gps['pixel_lat'] = (distinct_gps['latitude'] / 0.02).round() * 0.02
    distinct_gps['pixel_lon'] = (distinct_gps['longitude'] / 0.02).round() * 0.02
    
    # 4. Count unique GPS locations per pixel
    pixel_counts = distinct_gps.groupby(['pixel_lat', 'pixel_lon']).size().reset_index(name='site_count')
    pixel_counts = pixel_counts.sort_values('site_count', ascending=False)
    
    print(f"Summary: {len(pixel_counts)} unique pixels contain {len(distinct_gps)} distinct GPS sites.")
    print("\nTop 10 High-Density Pixels (Most sites per 2km cell):")
    print(pixel_counts.head(10).to_string(index=False))
    
    # Average sites per pixel
    print(f"\nAverage sites per pixel: {pixel_counts.site_count.mean():.2f}")

if __name__ == "__main__":
    count_sites_per_pixel()
