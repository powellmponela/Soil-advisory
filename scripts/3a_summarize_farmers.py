import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
DEMO_2019 = MAIZE_DIR / "maize_demo_2019.xlsx"

def summarize_farmers():
    # 1. Load all data
    df17 = pd.read_excel(TRIAL_2017)[["Farmer's name", "District", "VDC"]].dropna()
    df17['Year'] = 2017
    
    df18 = pd.read_csv(TRIAL_2018)[["Farmer's name", "District", "VDC"]].dropna()
    df18['Year'] = 2018
    
    df19 = pd.read_excel(DEMO_2019)[["Farmer's name", "District", "VDC"]].dropna()
    df19['Year'] = 2019
    
    all_raw = pd.concat([df17, df18, df19], ignore_index=True)
    
    # 2. Generate Universal Farmer ID
    all_raw['farmer_key'] = all_raw["Farmer's name"].str.strip().str.lower() + "_" + all_raw["District"].str.strip() + "_" + all_raw["VDC"].str.strip()
    
    unique_keys = sorted(all_raw['farmer_key'].unique())
    id_map = {key: f"FMR_{i+1:03d}" for i, key in enumerate(unique_keys)}
    all_raw['farmer_id'] = all_raw['farmer_key'].map(id_map)
    
    # 3. Summarize
    total_farmers = all_raw['farmer_id'].nunique()
    total_records = len(all_raw)
    
    print("=== Farmer Participation Summary (2017-2019) ===")
    print(f"Total Unique Farmers: {total_farmers}")
    print(f"Total Trial Records/Plots: {total_records}")
    print(f"Average Plots per Farmer: {total_records / total_farmers:.1f}")
    
    print("\n--- Farmers per Year ---")
    yearly_counts = all_raw.groupby('Year')['farmer_id'].nunique()
    print(yearly_counts.to_string())
    
    print("\n--- Multi-Year Participation ---")
    years_per_farmer = all_raw.groupby('farmer_id')['Year'].nunique()
    participation_counts = years_per_farmer.value_counts().sort_index()
    for years, count in participation_counts.items():
        print(f"Farmers participating in {years} year(s): {count}")
        
    print("\n--- Top 5 Farmers by Number of Plots Managed ---")
    top_farmers = all_raw.groupby('farmer_id').size().sort_values(ascending=False).head(5)
    for f_id, count in top_farmers.items():
        # Get district for context
        district = all_raw[all_raw['farmer_id'] == f_id]['District'].iloc[0]
        print(f"{f_id} ({district}): {count} plots")

if __name__ == "__main__":
    summarize_farmers()
