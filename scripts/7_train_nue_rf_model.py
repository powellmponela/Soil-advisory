import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from _project_paths import DATA_DIR, OUTPUT_ROOT

# File Paths
DATA_FILE = DATA_DIR / "nsaf_3year_trials_soil_efficiency.csv"
MODEL_PATH = OUTPUT_ROOT / "nue_rf_model.joblib"

def train_rf():
    # 1. Load Data
    df = pd.read_csv(DATA_FILE).dropna(subset=['ae_n', 'ph', 'om_pct', 'p_olsen_mg_kg', 'k_exch_mg_kg'])
    
    # 2. Features and Target
    features = ['ph', 'om_pct', 'n_total_pct', 'p_olsen_mg_kg', 'k_exch_mg_kg']
    X = df[features]
    y = df['ae_n']
    
    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Train
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. Evaluate
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    
    print(f"Random Forest Model Trained.")
    print(f"R-squared: {r2:.3f}")
    print(f"RMSE: {np.sqrt(mse):.3f}")
    
    # 6. Save
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to: {MODEL_PATH}")

if __name__ == "__main__":
    train_rf()
