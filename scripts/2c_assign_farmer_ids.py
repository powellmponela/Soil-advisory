import os

import pandas as pd
from _project_paths import DATA_DIR

# File Paths
MAIZE_DIR = DATA_DIR / "NSAF Crops Trial Data" / "Maize"
TRIAL_2017 = MAIZE_DIR / "maize_trials_2017.xlsx"
TRIAL_2018 = MAIZE_DIR / "maize_trials-2018.csv"
DEMO_2019 = MAIZE_DIR / "maize_demo_2019.xlsx"

# Processed files to update
FILE_2018_PROCESSED = DATA_DIR / "nsaf_plots_narc_soil.csv"
FILE_2019_PROCESSED = DATA_DIR / "nsaf_plots_narc_soil_2019.csv"

ID_COLUMNS = ["Farmer's name", "District", "VDC"]


def make_key(df):
    missing = [col for col in ID_COLUMNS if col not in df.columns]
    if missing:
        return pd.Series([pd.NA] * len(df), index=df.index)
    return (
        df["Farmer's name"].astype(str).str.strip().str.lower()
        + "_"
        + df["District"].astype(str).str.strip().str.lower()
        + "_"
        + df["VDC"].astype(str).str.strip().str.lower()
    )


def read_farmer_frame(path, reader):
    df = reader(path)
    available_cols = [col for col in ID_COLUMNS if col in df.columns]
    if len(available_cols) != len(ID_COLUMNS):
        print(f"Skipping farmer ID source with missing columns: {path}")
        return pd.DataFrame(columns=ID_COLUMNS)
    return df[ID_COLUMNS].dropna()


def add_farmer_ids_to_processed(path, id_map):
    if not os.path.exists(path):
        print(f"Processed file not found, skipped: {path}")
        return

    df_proc = pd.read_csv(path)
    if "farmer_id" in df_proc.columns and "Farmer's name" not in df_proc.columns:
        print(f"Farmer IDs already assigned or farmer names already removed: {path}")
        return

    key = make_key(df_proc)
    df_proc["farmer_id"] = key.map(id_map)
    drop_cols = [col for col in ["Farmer's name", "key"] if col in df_proc.columns]
    df_proc_clean = df_proc.drop(columns=drop_cols)
    df_proc_clean.to_csv(path, index=False)
    print(f"Updated processed file: {path}")


def generate_farmer_ids():
    df17 = read_farmer_frame(TRIAL_2017, pd.read_excel)
    df18 = read_farmer_frame(TRIAL_2018, pd.read_csv)
    df19 = read_farmer_frame(DEMO_2019, pd.read_excel)

    all_raw = pd.concat([df17, df18, df19], ignore_index=True)
    all_raw["key"] = make_key(all_raw)
    unique_keys = sorted(k for k in all_raw["key"].dropna().unique())
    id_map = {key: f"FMR_{i + 1:03d}" for i, key in enumerate(unique_keys)}
    print(f"Generated {len(id_map)} unique Farmer IDs.")

    add_farmer_ids_to_processed(FILE_2018_PROCESSED, id_map)
    add_farmer_ids_to_processed(FILE_2019_PROCESSED, id_map)


if __name__ == "__main__":
    generate_farmer_ids()
