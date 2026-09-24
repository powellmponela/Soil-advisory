import numpy as np
import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
PATH_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
PATH_2018 = MAIZE_DIR / "maize_trials-2018.csv"
PATH_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"
OUTPUT_FILE = DATA_DIR / "nsaf_3year_trials_soil_efficiency.csv"

def load_and_clean():
    # 1. 2017
    df17 = pd.read_excel(PATH_2017)
    df17 = df17.rename(columns={'Yield_t_ha': 'yield_t_ha', 'N_kg_ha': 'n_kg_ha', 'P2O5_kg_ha': 'p_kg_ha', 'K2O_kg_ha': 'k_kg_ha'})
    df17['year'] = 2017
    
    # 2. 2018
    df18 = pd.read_csv(PATH_2018)
    df18 = df18.rename(columns={'Yield_t_ha': 'yield_t_ha', 'N_kg_ha': 'n_kg_ha', 'P2O5_kg_ha': 'p_kg_ha', 'K2O_kg_ha': 'k_kg_ha'})
    df18['year'] = 2018
    
    # 3. 2019
    df19 = pd.read_csv(PATH_2019)
    # 2019 yield is kg/ha in some places, but demo has 'Yield_t_ha'
    # Actually, in demo_2019.xlsx, it might be kg/ha.
    # Let's check common columns
    df19 = df19.rename(columns={'Yield_kg_ha': 'yield_kg_ha', 'N_kg_ha': 'n_kg_ha', 'P2O5_kg_ha': 'p_kg_ha', 'K2O_kg_ha': 'k_kg_ha'})
    if 'yield_kg_ha' in df19.columns:
        df19['yield_t_ha'] = df19['yield_kg_ha'] / 1000
    df19['year'] = 2019

    # Combine
    cols = ['year', 'District', 'n_kg_ha', 'p_kg_ha', 'k_kg_ha', 'yield_t_ha', 'latitude', 'longitude']
    # Note: 2019 uses lat_fixed, lon_fixed
    df17_sub = df17[['year', 'District', 'n_kg_ha', 'p_kg_ha', 'k_kg_ha', 'yield_t_ha', 'latitude', 'longitude']]
    df18_sub = df18[['year', 'District', 'n_kg_ha', 'p_kg_ha', 'k_kg_ha', 'yield_t_ha', 'latitude', 'longitude']]
    df19_sub = df19[['year', 'District', 'n_kg_ha', 'p_kg_ha', 'k_kg_ha', 'yield_t_ha', 'lat_fixed', 'lon_fixed']]
    df19_sub.columns = cols
    
    all_trials = pd.concat([df17_sub, df18_sub, df19_sub], ignore_index=True)
    
    # 4. Calculate NUE & AE_N
    # We need a control baseline per year/district
    controls = all_trials[all_trials['n_kg_ha'] == 0].groupby(['year', 'District'])['yield_t_ha'].mean().reset_index(name='yield_control')
    all_trials = all_trials.merge(controls, on=['year', 'District'], how='left')
    
    # Global mean control for missing ones
    global_control = all_trials[all_trials['n_kg_ha'] == 0]['yield_t_ha'].mean()
    all_trials['yield_control'] = all_trials['yield_control'].fillna(global_control)
    
    all_trials['ae_n'] = (all_trials['yield_t_ha'] - all_trials['yield_control']) * 1000 / all_trials['n_kg_ha']
    all_trials['nue'] = all_trials['yield_t_ha'] * 1000 / all_trials['n_kg_ha']
    
    # Replace inf/nan
    all_trials.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # 5. Integrate Soil Data (Using matched 2018 as a proxy or re-fetching)
    # For now, let's join with the already matched 2018 soil data as a source of soil attributes
    # Actually, it's better to fetch NARC data for all points or use a lookup.
    # I'll use the matched 2018/2019 soil files I have.
    soil2018 = pd.read_csv(DATA_DIR / "nsaf_plots_narc_soil.csv")[["latitude", "longitude", "ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg"]].drop_duplicates()
    soil2019 = pd.read_csv(DATA_DIR / "nsaf_plots_narc_soil_2019.csv")[["lat_fixed", "lon_fixed", "ph", "om_pct", "n_total_pct", "p_olsen_mg_kg", "k_exch_mg_kg"]].drop_duplicates()
    soil2019.columns = soil2018.columns
    
    soil_all = pd.concat([soil2018, soil2019], ignore_index=True).drop_duplicates(subset=['latitude', 'longitude'])
    
    final_df = all_trials.merge(soil_all, on=['latitude', 'longitude'], how='inner')
    
    final_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Consolidated {len(final_df)} records with soil data and efficiency factors.")

if __name__ == "__main__":
    load_and_clean()
