import pandas as pd
import os
from _project_paths import DATA_DIR, OUTPUT_ROOT

def clean_file(file_path, cols_to_remove):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    df = pd.read_csv(file_path)
    removed = [c for c in cols_to_remove if c in df.columns]
    if removed:
        df = df.drop(columns=removed)
        df.to_csv(file_path, index=False)
        print(f"Cleaned {file_path}: removed {removed}")
    else:
        print(f"No personal info columns found in {file_path}")

def main():
    sensitive_cols = ['farmer_name', 'fmr_nm', 'cntct_no', "Farmer's name", 'contact_no']
    
    directories = [OUTPUT_ROOT, DATA_DIR]
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        print(f"\n--- Cleaning Directory: {directory} ---")
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                clean_file(os.path.join(directory, file), sensitive_cols)

if __name__ == "__main__":
    main()
