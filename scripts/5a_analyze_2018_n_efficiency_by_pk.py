import pandas as pd
from _project_paths import DATA_DIR, OUTPUT_ROOT

# File Paths
DATA_2018 = DATA_DIR / "nsaf_plots_narc_soil.csv"

def analyze_n_efficiency_given_pk():
    # 1. Load Data
    df = pd.read_csv(DATA_2018)
    
    # 2. Filter out control (N=0) to calculate AE_N
    # But wait, AE_N needs a control. 
    # Let's find the mean yield for N=0 in each District/VDC if possible
    controls = df[df['N_kg_ha'] == 0].groupby(['District'])['Yield_t_ha'].mean().reset_index(name='yield_control')
    
    df = df.merge(controls, on='District', how='left')
    df['AE_N_calc'] = (df['Yield_t_ha'] - df['yield_control']) * 1000 / df['N_kg_ha']
    
    # Remove cases where N=0 or control is missing
    df_eff = df[(df['N_kg_ha'] > 0) & (df['yield_control'].notna())].copy()
    
    # 3. Define PK Scenarios
    def get_pk_scenario(row):
        p = row['P2O5_kg_ha']
        k = row['K2O_kg_ha']
        if p == 0 and k == 0:
            return "Zero PK"
        elif p < 60 or k < 40:
            return "Sub-optimal PK"
        else:
            return "Full PK (60:40)"

    df_eff['PK_Scenario'] = df_eff.apply(get_pk_scenario, axis=1)
    
    # 4. Aggregate Results
    summary = df_eff.groupby('PK_Scenario').agg({
        'Yield_t_ha': 'mean',
        'AE_N_calc': 'mean',
        'N_kg_ha': 'mean'
    }).reset_index()
    
    summary.columns = ['PK Scenario', 'Avg Yield (t/ha)', 'AE-N (kg grain/kg N)', 'Avg N Applied (kg/ha)']
    
    # 5. Estimate N Demand for 8.0 t/ha Target (Standard QUEFTS target)
    avg_control = df['yield_control'].mean()
    target_yield = 8.0
    
    summary['N Demand for 8t/ha'] = (target_yield - avg_control) * 1000 / summary['AE-N (kg grain/kg N)']
    summary['N Demand for 8t/ha'] = summary['N Demand for 8t/ha'].apply(lambda x: max(0, x))
    
    print("\nN Efficiency and Demand Given P & K Levels (2018 Data):")
    print(summary.to_string(index=False))
    
    # Save results
    summary.to_csv(OUTPUT_ROOT / "n_efficiency_by_pk_2018.csv", index=False)

if __name__ == "__main__":
    analyze_n_efficiency_given_pk()
