import pandas as pd
from _project_paths import OUTPUT_ROOT

# File Paths
DATA_2019 = OUTPUT_ROOT / "maize_2019_demo_plot_results.csv"

def analyze_n_response_2019():
    # 1. Load Data
    df = pd.read_csv(DATA_2019)
    
    # 2. Yield Gap (Target 8.0 t/ha)
    target_yield = 8.0
    
    # 3. Analyze N Rates
    # The 2019 demos have specific N rates: 60, 78, 120
    # Let's group by N_kg_ha and calculate means
    summary = df.groupby('N_kg_ha').agg({
        'Yield_t_ha': 'mean',
        'AE_pooled': 'mean'
    }).reset_index()
    
    # AE_pooled is (Yield - Yield_control_pooled) * 1000 / N
    # Note: Yield_t_ha in the output file might be kg/ha if I didn't fix it there.
    # Let's check. In analyze_2019_demos.R, Yield_t_ha is t/ha.
    
    summary.columns = ['N Rate (kg/ha)', 'Avg Yield (t/ha)', 'AE-N (kg grain/kg N)']
    
    # 4. Estimate N Demand for 8t/ha target based on observed AE
    # N_demand = (Target - Control) * 1000 / AE
    # We need the average control yield used in the R script.
    # It was 6.7 in the 2018 data, let's check for 2019 pooled.
    avg_control = df['yield_control_pooled'].mean()
    
    summary['N Demand for 8t/ha'] = (target_yield - avg_control) * 1000 / summary['AE-N (kg grain/kg N)']
    
    print("\nNitrogen Response Summary (2019 Demos, Fixed P:60, K:40):")
    print(summary.to_string(index=False))
    
    # Save results
    summary.to_csv(OUTPUT_ROOT / "n_response_summary_2019.csv", index=False)

if __name__ == "__main__":
    analyze_n_response_2019()
