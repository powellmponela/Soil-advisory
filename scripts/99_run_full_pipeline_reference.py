import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from _project_paths import DATA_DIR, OUTPUT_ROOT

# Paths
OUTPUT_DIR = OUTPUT_ROOT
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NSAF_SOIL_FILE = os.path.join(DATA_DIR, "nsaf_plots_narc_soil.csv")
DSM_FILE = os.path.join(DATA_DIR, "dsm_western_terai_midhill_pixel-centroid.csv")

TARGET_YIELD_KG_HA = 8000.0

def quefts_proxy_ins(df):
    """
    Computes a simplified proxy for Indigenous Nutrient Supply based on 
    standard generic QUEFTS principles for tropical soils.
    """
    # INS (Indigenous N Supply) kg/ha
    ins = (df['om_pct'] * 15) + (df['n_total_pct'] * 100)
    # IPS (Indigenous P Supply) kg/ha
    ips = df['p_olsen_mg_kg'] * 0.5
    # IKS (Indigenous K Supply) kg/ha
    iks = df['k_exch_mg_kg'] * 0.3
    
    return ins, ips, iks

def main():
    print("--- Loading NSAF Soil Harmonized Data ---")
    nsaf_df = pd.read_csv(NSAF_SOIL_FILE)
    
    # Target and Features
    features = ['ph', 'om_pct', 'n_total_pct', 'p_olsen_mg_kg', 'k_exch_mg_kg']
    target = 'AE_N'
    
    # Clean missing values
    model_df = nsaf_df.dropna(subset=features + [target]).copy()
    print(f"Data points available for RF modeling: {len(model_df)}")
    
    X = model_df[features]
    y = model_df[target]
    
    print("\n--- Training Random Forest Empirical Model (AE_N) ---")
    rf = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=8)
    
    # Cross-validation R-squared
    cv_r2 = cross_val_score(rf, X, y, cv=5, scoring='r2').mean()
    print(f"5-Fold CV R-squared for AE_N: {cv_r2:.3f}")
    
    # Train final model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    rf.fit(X_train, y_train)
    test_r2 = r2_score(y_test, rf.predict(X_test))
    print(f"Holdout Test R-squared: {test_r2:.3f}")
    
    # Feature Importance
    importances = pd.DataFrame({
        'Feature': features,
        'Importance': rf.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    print("\nFeature Importances:")
    print(importances)
    importances.to_csv(os.path.join(OUTPUT_DIR, "rf_feature_importances.csv"), index=False)
    
    print("\n--- Processing DSM Spatial Data ---")
    dsm_df = pd.read_csv(DSM_FILE)
    print(f"Loaded DSM Pixels: {len(dsm_df)}")
    
    # Predict AE-N for the spatial grid
    dsm_df['predicted_AE_N'] = rf.predict(dsm_df[features])
    
    print("\n--- Applying QUEFTS Proxy ---")
    ins, ips, iks = quefts_proxy_ins(dsm_df)
    dsm_df['INS_kg_ha'] = ins
    dsm_df['IPS_kg_ha'] = ips
    dsm_df['IKS_kg_ha'] = iks
    
    # Base yield from INS assuming 40 kg grain per kg N uptake (generic)
    base_yield_n = dsm_df['INS_kg_ha'] * 40
    dsm_df['base_yield_kg_ha'] = base_yield_n
    
    # Yield Gap
    dsm_df['yield_gap_kg_ha'] = np.maximum(0, TARGET_YIELD_KG_HA - dsm_df['base_yield_kg_ha'])
    
    # Required Fertilizer N based on predicted AE-N
    # N Demand = Yield Gap / Agronomic Efficiency of N
    dsm_df['N_demand_kg_ha'] = dsm_df['yield_gap_kg_ha'] / dsm_df['predicted_AE_N']
    
    # Cap absurd values
    dsm_df['N_demand_kg_ha'] = dsm_df['N_demand_kg_ha'].clip(upper=300)
    
    out_file = os.path.join(OUTPUT_DIR, "spatial_advisory_results.csv")
    dsm_df.to_csv(out_file, index=False)
    print(f"\nSpatial advisory map generated: {out_file}")
    print("Mean N-Demand (kg/ha):", dsm_df['N_demand_kg_ha'].mean())
    print("Mean Predicted AE-N:", dsm_df['predicted_AE_N'].mean())
    print("DONE.")

if __name__ == "__main__":
    main()
