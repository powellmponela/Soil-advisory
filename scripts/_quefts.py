"""Python equivalents of the Rquefts functions used by this project."""

from __future__ import annotations

import numpy as np
import pandas as pd


def nut_supply_1(ph, soc, kex, polsen, ptotal=None):
    """Reproduce Rquefts::nutSupply1 (Janssen et al., 1990, Table 2).

    Inputs may be scalars, NumPy arrays, or pandas Series. SOC is g/kg,
    Kex is mmol/kg, and P values are mg/kg. Returned values are kg/ha.
    """
    ph = np.asarray(ph, dtype=float)
    soc = np.asarray(soc, dtype=float)
    kex = np.asarray(kex, dtype=float)
    polsen = np.asarray(polsen, dtype=float)
    ph, soc, kex, polsen = np.broadcast_arrays(ph, soc, kex, polsen)

    f_n = 0.25 * (ph - 3.0)
    n_supply = f_n * 6.8 * soc

    f_p = 1.0 - 0.5 * (ph - 6.0) ** 2
    p_supply = f_p * 0.35 * soc + 0.5 * polsen
    if ptotal is not None:
        ptotal = np.broadcast_to(np.asarray(ptotal, dtype=float), ph.shape)
        use_total = ~np.isnan(ptotal)
        p_supply = np.where(
            use_total, f_p * 0.014 * ptotal + 0.5 * polsen, p_supply
        )

    f_k = 0.625 * (3.4 - 0.4 * ph)
    k_supply = (f_k * 400.0 * kex) / (2.0 + 0.9 * soc)

    result = np.column_stack((n_supply.ravel(), p_supply.ravel(), k_supply.ravel()))
    result[result < 0] = 0
    if result.shape[0] == 1:
        return tuple(result[0])
    return pd.DataFrame(result, columns=["n_supply", "p_supply", "k_supply"])


def add_quefts_soil_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """Add the soil-unit conversions used consistently by the R scripts."""
    out = df.copy()
    out["OC"] = (pd.to_numeric(out["om_pct"], errors="coerce") / 1.724) * 10.0
    out["P_Olsen"] = pd.to_numeric(out["p_olsen_mg_kg"], errors="coerce") / 2.6
    out["Exch_K"] = (
        pd.to_numeric(out["k_exch_mg_kg"], errors="coerce") * 0.83 / 2.6
    ) / 39.1
    return out


def add_native_supply(df: pd.DataFrame) -> pd.DataFrame:
    """Append vectorized native N, P, and K supply columns."""
    out = df.copy()
    supply = nut_supply_1(out["ph"], out["OC"], out["Exch_K"], out["P_Olsen"])
    out[["n_supply", "p_supply", "k_supply"]] = supply.to_numpy()
    return out


def add_target_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """Add fertilizer recommendations for the R scripts' 8 t/ha target."""
    out = df.copy()
    out["rec_N_kg_ha"] = ((200.0 - out["n_supply"]) / 0.5).clip(lower=0)
    out["rec_P2O5_kg_ha"] = ((40.0 - out["p_supply"]) / 0.2).clip(lower=0) * 2.29
    out["rec_K2O_kg_ha"] = ((200.0 - out["k_supply"]) / 0.5).clip(lower=0) * 1.21
    return out
