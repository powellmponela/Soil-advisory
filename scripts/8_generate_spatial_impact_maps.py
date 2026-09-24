"""Generate spatial AE-N, nitrogen-demand, and yield-gap outputs."""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

DSM_FILE = DATA_DIR / "dsm_western_terai_midhill_pixel-centroid.csv"
MODEL_PATH = OUTPUT_ROOT / "nue_rf_model.joblib"
OUTPUT_DIR = OUTPUT_ROOT / "maps"


def generate_spatial_results() -> None:
    """Apply the trained model to the DSM grid and save maps and data."""
    # A workflow subprocess cannot use Positron's interactive plotting backend.
    # Agg renders PNG files without requiring Positron or another GUI backend.
    plt.switch_backend("Agg")

    model = joblib.load(MODEL_PATH)
    grid = pd.read_csv(DSM_FILE)

    features = [
        "ph",
        "om_pct",
        "n_total_pct",
        "p_olsen_mg_kg",
        "k_exch_mg_kg",
    ]
    model_inputs = grid[features].fillna(grid[features].mean())
    grid["pred_ae_n"] = model.predict(model_inputs)

    grid["yield_gap"] = np.maximum(0, 8.0 - (grid["om_pct"] * 1.5))
    grid["n_demand_kg_ha"] = (
        grid["yield_gap"] * 1000 / grid["pred_ae_n"]
    ).clip(0, 250)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def plot_map(
        column: str,
        title: str,
        filename: str,
        colour_map: str = "viridis",
    ) -> None:
        plt.figure(figsize=(10, 6))
        scatter = plt.scatter(
            grid["lon"],
            grid["lat"],
            c=grid[column],
            cmap=colour_map,
            s=5,
            alpha=0.6,
        )
        plt.colorbar(scatter, label=title)
        plt.title(f"Spatial Distribution of {title} in Western Nepal")
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight")
        plt.close()

    plot_map(
        "pred_ae_n",
        "Agronomic Efficiency (AE-N)",
        "map_ae_n_spatial.png",
        "YlGn",
    )
    plot_map(
        "n_demand_kg_ha",
        "Nitrogen Demand (kg/ha)",
        "map_n_demand_spatial.png",
        "RdYlGn_r",
    )
    plot_map(
        "yield_gap",
        "Yield Gap (t/ha)",
        "map_yield_gap_spatial.png",
        "OrRd",
    )

    grid.to_csv(OUTPUT_DIR / "spatial_impact_results.csv", index=False)
    print(f"Spatial impact results and maps generated in: {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_spatial_results()
