import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
PROCESSED_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"

def analyze_sites():
    # 1. Load 2017
    df17 = pd.read_excel(TRIAL_2017)
    sites17 = df17[['latitude', 'longitude']].dropna()
    sites17['Year'] = 2017
    
    # 2. Load 2018
    df18 = pd.read_csv(TRIAL_2018)
    sites18 = df18[['latitude', 'longitude']].dropna()
    sites18['Year'] = 2018
    
    # 3. Load 2019
    df19 = pd.read_csv(PROCESSED_2019)
    sites19 = df19[['lat_fixed', 'lon_fixed']].rename(
        columns={'lat_fixed': 'latitude', 'lon_fixed': 'longitude'}
    ).dropna()
    sites19['Year'] = 2019
    
    # 4. Combine
    all_sites = pd.concat([sites17, sites18, sites19], ignore_index=True)
    
    # Round to 4 decimal places (~11m precision) to identify repeat sites
    all_sites['lat_round'] = all_sites['latitude'].round(4)
    all_sites['lon_round'] = all_sites['longitude'].round(4)
    
    distinct_sites = all_sites[['lat_round', 'lon_round']].drop_duplicates()
    
    print(f"Total Trial Records (All Years): {len(all_sites)}")
    print(f"Distinct GPS Locations (Sites): {len(distinct_sites)}")
    
    # Breakdown by year
    print("\nRecords per Year:")
    print(all_sites['Year'].value_counts().sort_index())
    
    # Repeated sites
    site_counts = all_sites.groupby(['lat_round', 'lon_round']).size().reset_index(name='visits')
    repeated = site_counts[site_counts.visits > 1]
    print(f"\nNumber of sites visited more than once (multiple records/treatments): {len(repeated)}")

if __name__ == "__main__":
    analyze_sites()
