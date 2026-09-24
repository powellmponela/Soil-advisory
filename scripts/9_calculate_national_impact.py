import pandas as pd
from _project_paths import OUTPUT_ROOT

# File Paths
TRIALS_2019 = OUTPUT_ROOT / "maize_2019_demo_plot_results.csv"
QUEFTS_PIXELS = OUTPUT_ROOT / "maize_quefts_western_highres_pixels.csv"
OUTPUT_REPORT = OUTPUT_ROOT / "national_impact_summary.csv"

# Assumptions
MAIZE_AREA_NEPAL_HA = 950000

def calculate_impact():
    # 1. Load Data
    df_trials = pd.read_csv(TRIALS_2019)
    df_quefts = pd.read_csv(QUEFTS_PIXELS)

    # 2. Yield Gap Analysis (t/ha)
    y_actual = df_trials['Yield_t_ha'].mean()
    y_potential = 8.0 # Target in QUEFTS
    yield_gap = y_potential - y_actual

    # 3. Fertilizer Analysis (kg/ha)
    # Actual (Demo Plots)
    n_actual = df_trials['N_kg_ha'].mean()
    p_actual = df_trials['P2O5_kg_ha'].mean()
    k_actual = df_trials['K2O_kg_ha'].mean()

    # Recommended (QUEFTS Pixels)
    n_rec = df_quefts['rec_N_kg_ha'].mean()
    p_rec = df_quefts['rec_P2O5_kg_ha'].mean()
    k_rec = df_quefts['rec_K2O_kg_ha'].mean()

    # Savings / Over-application (Negative means we need more)
    n_savings = n_actual - n_rec
    p_savings = p_actual - p_rec
    k_savings = k_actual - k_rec

    # 4. National Extrapolation (Tonnes)
    total_yield_gain = yield_gap * MAIZE_AREA_NEPAL_HA
    total_n_demand = n_rec * MAIZE_AREA_NEPAL_HA / 1000
    total_p_demand = p_rec * MAIZE_AREA_NEPAL_HA / 1000
    total_k_demand = k_rec * MAIZE_AREA_NEPAL_HA / 1000

    # 5. Summary
    summary = {
        "Metric": ["Yield Actual (t/ha)", "Yield Potential (t/ha)", "Yield Gap (t/ha)", 
                   "N Actual (kg/ha)", "N Recommended (kg/ha)", "N Savings (kg/ha)",
                   "P2O5 Actual (kg/ha)", "P2O5 Recommended (kg/ha)", "P2O5 Savings (kg/ha)",
                   "K2O Actual (kg/ha)", "K2O Recommended (kg/ha)", "K2O Savings (kg/ha)",
                   "Total Potential Yield Gain (Mt)", "National N Demand (1000 t)", 
                   "National P2O5 Demand (1000 t)", "National K2O Demand (1000 t)"],
        "Value": [y_actual, y_potential, yield_gap, 
                  n_actual, n_rec, n_savings,
                  p_actual, p_rec, p_savings,
                  k_actual, k_rec, k_savings,
                  total_yield_gain / 1e6, total_n_demand / 1,
                  total_p_demand / 1, total_k_demand / 1]
    }

    df_summary = pd.DataFrame(summary)
    df_summary['Value'] = df_summary['Value'].round(2)
    
    print("\nAgronomic Impact Summary:")
    print(df_summary.to_string(index=False))
    
    df_summary.to_csv(OUTPUT_REPORT, index=False)
    print(f"\nSummary saved to: {OUTPUT_REPORT}")

if __name__ == "__main__":
    calculate_impact()
