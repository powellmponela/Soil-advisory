import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
PROCESSED_2019 = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"

def count_farmers_per_pixel():
    # 1. Load All Trial Data with Farmer Info
    df17 = pd.read_excel(TRIAL_2017)
    df17 = df17[["Farmer's name", "District", "VDC", "latitude", "longitude"]].dropna()
    df17['farmer_id'] = df17["Farmer's name"].str.strip().str.lower() + "_" + df17["District"] + "_" + df17["VDC"]
    df17['Year'] = 2017

    df18 = pd.read_csv(TRIAL_2018)
    df18 = df18[["Farmer's name", "District", "VDC", "latitude", "longitude"]].dropna()
    df18['farmer_id'] = df18["Farmer's name"].str.strip().str.lower() + "_" + df18["District"] + "_" + df18["VDC"]
    df18['Year'] = 2018

    df19 = pd.read_csv(PROCESSED_2019)
    df19 = df19[["farmer_id", "District", "VDC", "lat_fixed", "lon_fixed"]].dropna()
    df19 = df19.rename(columns={"lat_fixed": "latitude", "lon_fixed": "longitude"})
    df19['Year'] = 2019

    common = ['farmer_id', 'District', 'VDC', 'latitude', 'longitude', 'Year']
    all_data = pd.concat([df17[common], df18[common], df19[common]], ignore_index=True)
    
    # 2. Map to 0.02-degree pixels
    all_data['pixel_lat'] = (all_data['latitude'] / 0.02).round() * 0.02
    all_data['pixel_lon'] = (all_data['longitude'] / 0.02).round() * 0.02
    
    # 3. Count unique farmers per pixel
    pixel_farmer_counts = all_data.groupby(['pixel_lat', 'pixel_lon'])['farmer_id'].nunique().reset_index(name='farmer_count')
    pixel_farmer_counts = pixel_farmer_counts.sort_values('farmer_count', ascending=False)
    
    # Compare with total record count
    pixel_record_counts = all_data.groupby(['pixel_lat', 'pixel_lon']).size().reset_index(name='record_count')
    summary = pixel_farmer_counts.merge(pixel_record_counts, on=['pixel_lat', 'pixel_lon'])
    
    print(f"Summary: {len(summary)} unique pixels cover {all_data['farmer_id'].nunique()} unique farmers.")
    print("\nTop 10 High-Density Pixels (Most Farmers per 2km cell):")
    print(summary.head(10).to_string(index=False))
    
    # Average farmers per pixel
    print(f"\nAverage farmers per pixel: {summary.farmer_count.mean():.2f}")

if __name__ == "__main__":
    count_farmers_per_pixel()
