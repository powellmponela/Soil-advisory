"""Python counterpart of 0c_nsaf_data_legacy.R.

Harmonizes the 2017-2019 NSAF summer-maize trials to the same Carob-like
schema and creates the same CSV and Excel deliverables as the R script.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize"
OUT = ROOT / "outputs"
F2017 = DATA / "maize_trials_2017.xlsx"
F2018 = DATA / "maize_trials-2018.csv"
F2019 = DATA / "Maize_postharvest_2019 - all versions - labels - 2020-01-23-04-01-40.xlsx"
ILLEGAL_EXCEL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

CAROB_COLS = [
    "dataset_id", "source_file", "source_sheet", "country", "crop", "year", "season",
    "adm1", "adm2", "site", "trial_id", "farmer_id", "farmer_name", "observation_id",
    "trial_type", "treatment_code", "treatment", "treatment_group", "barcode",
    "N_fertilizer_kg_ha", "P2O5_fertilizer_kg_ha", "K2O_fertilizer_kg_ha",
    "B_fertilizer_kg_ha", "ZnSO4_fertilizer_kg_ha", "organic_fertilizer_t_ha",
    "N_source", "N_application_method", "N_application_time", "variety",
    "seed_rate_kg_ha", "planting_window", "plant_spacing", "plant_density_ha",
    "latitude", "longitude", "elevation_m", "gps_precision_m", "soil_pH", "soil_OM_pct",
    "soil_N", "soil_P", "soil_K", "straw_yield_kg_ha", "cob_yield_kg_ha",
    "grain_yield_raw_kg_ha", "thousand_grain_weight_g", "grain_moisture_pct",
    "yield_kg_ha", "yield_t_ha", "PFPN_kg_grain_per_kg_N",
    "AE_N_kg_grain_per_kg_N", "notes",
]


def sanitize_excel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove control characters that are prohibited in Excel XML cells."""
    clean = frame.copy()
    for column in clean.select_dtypes(include=["object", "string"]).columns:
        clean[column] = clean[column].map(
            lambda value: ILLEGAL_EXCEL_CHARACTERS.sub("", value)
            if isinstance(value, str)
            else value
        )
    return clean

TEXT_MAP = {
    "season": ["Season", "season"], "adm1": ["District", "district"],
    "adm2": ["VDC", "vdc", "Municipality", "municipality"],
    "farmer_id": ["Farmer_id", "farmer_id", "Farmer ID"],
    "farmer_name": ["Farmer's name", "Farmer name", "farmer_name"],
    "trial_type": ["Trial/Demo", "trial_type"], "barcode": ["barcode", "Barcode"],
    "treatment_group": ["category", "Category", "treatment_group"],
    "N_source": ["N_source", "N source"],
    "N_application_method": ["N_methods", "N_method", "N application method"],
    "N_application_time": ["N_time", "N timing", "N_application_time"],
    "variety": ["variety", "Variety"],
    "planting_window": ["planting time", "planting_time", "Planting time"],
    "plant_spacing": ["spacing (cm*cm)", "plant_spacing", "Spacing"],
}

NUM_MAP = {
    "N_fertilizer_kg_ha": ["N_kg_ha", "N_fertilizer_kg_ha"],
    "P2O5_fertilizer_kg_ha": ["P2O5_kg_ha", "P2O5_fertilizer_kg_ha"],
    "K2O_fertilizer_kg_ha": ["K2O_kg_ha", "K2O_fertilizer_kg_ha"],
    "B_fertilizer_kg_ha": ["B_kg_ha", "B_fertilizer_kg_ha"],
    "ZnSO4_fertilizer_kg_ha": ["ZnSO4_kg_ha", "ZnSO4_fertilizer_kg_ha"],
    "organic_fertilizer_t_ha": ["FYM_t_ha", "organic_fertilizer_t_ha"],
    "seed_rate_kg_ha": ["seed_rate_kg_ha", "Seed rate"],
    "plant_density_ha": ["plant_population", "plant_density_ha"],
    "latitude": ["latitude", "Latitude"], "longitude": ["longitude", "Longitude"],
    "elevation_m": ["altitude", "elevation_m", "Elevation"],
    "gps_precision_m": ["precision", "gps_precision_m"], "soil_pH": ["pH", "soil_pH"],
    "soil_OM_pct": ["OM", "soil_OM_pct"], "soil_N": ["N", "soil_N"],
    "soil_P": ["P", "soil_P"], "soil_K": ["K", "soil_K"],
    "straw_yield_kg_ha": ["Straw_wt_kg_ha", "straw_weight_kg_ha", "straw_yield_kg_ha"],
    "cob_yield_kg_ha": ["cob_wt_kg_ha", "cob_yield_kg_ha"],
    "grain_yield_raw_kg_ha": ["grain_yield_kg_ha", "grain_yield_raw_kg_ha"],
    "thousand_grain_weight_g": ["1000_grain_wt_gm", "thousand_grain_weight_g"],
    "grain_moisture_pct": ["moisture%", "grain_moisture_pct"],
    "yield_kg_ha": ["Yield_kg_ha", "yield_kg_ha"], "yield_t_ha": ["Yield_t_ha", "yield_t_ha"],
    "PFPN_kg_grain_per_kg_N": ["NUE_N", "PFPN", "PFPN_kg_grain_per_kg_N"],
    "AE_N_kg_grain_per_kg_N": ["AE_N", "AE_N_kg_grain_per_kg_N"],
}


def first_col(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for name in candidates:
        if name in df.columns:
            return df[name]
    return pd.Series(pd.NA, index=df.index, dtype="object")


def text_col(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    out = first_col(df, candidates).astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    return out.mask(out.eq(""))


def number_col(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    raw = first_col(df, candidates).astype("string")
    extracted = raw.str.replace(",", "", regex=False).str.extract(r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)", expand=False)
    return pd.to_numeric(extracted, errors="coerce")


def sheet(path: Path, preferred: str) -> str:
    names = pd.ExcelFile(path).sheet_names
    return preferred if preferred in names else names[0]


def standard_year(df: pd.DataFrame, year: int, source: Path, source_sheet: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["dataset_id"] = f"nsaf_maize_trials_{year}"
    out["source_file"], out["source_sheet"] = source.name, source_sheet
    out["country"], out["crop"], out["year"] = "Nepal", "maize", year
    for target, candidates in TEXT_MAP.items():
        out[target] = text_col(df, candidates)
    for target, candidates in NUM_MAP.items():
        out[target] = number_col(df, candidates)
    out["site"] = out["adm1"].fillna("") + " | " + out["adm2"].fillna("")
    out.loc[out["adm1"].isna(), "site"] = out.loc[out["adm1"].isna(), "adm2"]
    out.loc[out["adm2"].isna(), "site"] = out.loc[out["adm2"].isna(), "adm1"]
    obs_candidates = ["ID", "id", "S.no", "S.No"] if year == 2017 else ["S.no", "S.No", "ID", "id"]
    out["observation_id"] = text_col(df, obs_candidates)
    if year == 2017:
        source_year = number_col(df, ["Year", "year", "YEAR"]).fillna(2017)
        out["year"] = source_year
        out["trial_id"] = source_year.astype("Int64").astype("string") + "_" + out["farmer_id"]
        out["treatment_code"] = text_col(df, ["treatment_code", "Treatment code", "treatment"])
        out["treatment"] = text_col(df, ["treatment", "Treatment", "treatment_label"]).fillna(out["treatment_code"])
    else:
        out["trial_id"] = ("2018_" + out["adm1"] + "_" + out["adm2"] + "_" + out["farmer_name"])
        out["treatment_code"] = text_col(df, ["treatment", "Treatment", "treatment_code"])
        labels = {
            "1": "NPK urea split (120-60-40)", "2": "NPK PCU basal (120-60-40)",
            "3": "N60 PCU basal (60-60-40)", "4": "UDP basal (78-60-40)",
            "5": "N60 urea split (60-60-40)", "6": "P omission urea split (120-0-40)",
            "7": "N omission (0-60-40)", "8": "Control (0-0-0)",
            "9": "NPK urea split V6/V10 (120-60-40)",
        }
        out["treatment"] = out["treatment_code"].map(labels).fillna(out["treatment_code"])
    out["yield_t_ha"] = out["yield_t_ha"].fillna(out["yield_kg_ha"] / 1000)
    out["notes"] = pd.NA
    return out.reindex(columns=CAROB_COLS)


def positional_number(df: pd.DataFrame, r_position: int) -> pd.Series:
    if r_position <= len(df.columns):
        return pd.to_numeric(df.iloc[:, r_position - 1], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def positional_text(df: pd.DataFrame, r_position: int) -> pd.Series:
    if r_position <= len(df.columns):
        return df.iloc[:, r_position - 1].astype("string").str.strip().mask(lambda x: x.eq(""))
    return pd.Series(pd.NA, index=df.index, dtype="string")


def year_2019(df: pd.DataFrame, source_sheet: str) -> pd.DataFrame:
    district_raw = text_col(df, ["District", "district"])
    adm1 = district_raw.replace({"Surket": "Surkhet"})
    adm2 = pd.Series(pd.NA, index=df.index, dtype="string")
    for district in ["Surket", "Surkhet", "Dang", "Palpa", "Kavre", "Doti", "Nuwakot", "Makwanpur", "Salyan", "Chitwan"]:
        candidates = ["Surket", "Surkhet"] if district in {"Surket", "Surkhet"} else [district]
        values = text_col(df, candidates)
        adm2.loc[district_raw.eq(district)] = values.loc[district_raw.eq(district)]
    trial_id = text_col(df, ["_uuid", "uuid", "ID", "id"])
    blocks = []
    starts = {**{f"T{i+1}": 17 + 12*i for i in range(10)},
              **{f"A{i+1}": 137 + 12*i for i in range(5)},
              **{f"B{i+1}": 197 + 12*i for i in range(5)}}
    for code, start in starts.items():
        block = pd.DataFrame(index=df.index)
        block["dataset_id"], block["source_file"], block["source_sheet"] = "maize_postharvest_2019", F2019.name, source_sheet
        block["country"], block["crop"], block["year"] = "Nepal", "maize", 2019
        block["season"] = text_col(df, ["Season", "season"])
        block["adm1"], block["adm2"] = adm1, adm2
        block["site"] = adm1.fillna("") + " | " + adm2.fillna("")
        block["farmer_id"] = text_col(df, ["Farmer_id", "farmer_id", "Farmer ID"])
        block["farmer_name"] = text_col(df, ["Farmer's name", "Farmer name", "farmer_name"])
        block["trial_id"], block["observation_id"] = trial_id, trial_id + "_" + code
        block["trial_type"] = text_col(df, ["Trial/Demo", "trial_type"])
        block["treatment_code"], block["treatment"] = code, code
        block["treatment_group"] = code[0] + " block"
        block["barcode"] = positional_text(df, start)
        block["latitude"], block["longitude"] = positional_number(df, start+2), positional_number(df, start+3)
        block["elevation_m"], block["gps_precision_m"] = positional_number(df, start+4), positional_number(df, start+5)
        block["straw_yield_kg_ha"] = positional_number(df, start+6)
        block["cob_yield_kg_ha"] = positional_number(df, start+7)
        block["grain_yield_raw_kg_ha"] = positional_number(df, start+8)
        block["thousand_grain_weight_g"] = positional_number(df, start+9)
        block["grain_moisture_pct"] = positional_number(df, start+10)
        block["yield_kg_ha"] = positional_number(df, start+11)
        block["yield_t_ha"] = block["yield_kg_ha"] / 1000
        block["notes"] = "2019 wide postharvest file reshaped from treatment blocks; fertilizer rates were not embedded in the source file."
        block = block.reindex(columns=CAROB_COLS)
        blocks.append(block.loc[block["barcode"].notna() | block["yield_kg_ha"].notna()])
    return pd.concat(blocks, ignore_index=True)


def unique_count(series: pd.Series) -> int:
    return series.dropna().nunique()


def joined_unique(series: pd.Series) -> str:
    return "; ".join(sorted(series.dropna().astype(str).unique()))


def main() -> None:
    missing = [p for p in [F2017, F2018, F2019] if not p.exists()]
    if missing:
        raise FileNotFoundError("These files were not found:\n" + "\n".join(map(str, missing)))
    s17, s19 = sheet(F2017, "maize_trials_2017"), sheet(F2019, "Maize_postharvest_2019")
    d17 = standard_year(pd.read_excel(F2017, sheet_name=s17), 2017, F2017, s17)
    d18 = standard_year(pd.read_csv(F2018), 2018, F2018, "maize_trials-2018")
    d19 = year_2019(pd.read_excel(F2019, sheet_name=s19), s19)
    merged = pd.concat([d17, d18, d19], ignore_index=True)[CAROB_COLS]
    merged = merged.sort_values(["year", "adm1", "adm2", "farmer_name", "treatment_code"], na_position="last")

    keys = ["year", "adm1", "adm2", "site", "treatment_code", "treatment", "treatment_group"]
    grouped = merged.groupby(keys, dropna=False)
    summary = grouped.agg(
        n_obs=("year", "size"), n_trials=("trial_id", unique_count),
        n_farmers=("farmer_name", unique_count), n_yield=("yield_kg_ha", "count"),
        mean_yield_kg_ha=("yield_kg_ha", "mean"), sd_yield_kg_ha=("yield_kg_ha", "std"),
        min_yield_kg_ha=("yield_kg_ha", "min"), max_yield_kg_ha=("yield_kg_ha", "max"),
        mean_yield_t_ha=("yield_t_ha", "mean"),
        mean_N_fertilizer_kg_ha=("N_fertilizer_kg_ha", "mean"),
        mean_P2O5_fertilizer_kg_ha=("P2O5_fertilizer_kg_ha", "mean"),
        mean_K2O_fertilizer_kg_ha=("K2O_fertilizer_kg_ha", "mean"),
        mean_organic_fertilizer_t_ha=("organic_fertilizer_t_ha", "mean"),
        mean_PFPN_kg_grain_per_kg_N=("PFPN_kg_grain_per_kg_N", "mean"),
        mean_AE_N_kg_grain_per_kg_N=("AE_N_kg_grain_per_kg_N", "mean"),
        mean_straw_yield_kg_ha=("straw_yield_kg_ha", "mean"),
        mean_cob_yield_kg_ha=("cob_yield_kg_ha", "mean"),
        mean_grain_yield_raw_kg_ha=("grain_yield_raw_kg_ha", "mean"),
        mean_grain_moisture_pct=("grain_moisture_pct", "mean"),
        source_datasets=("dataset_id", joined_unique),
    ).reset_index().sort_values(["year", "adm1", "adm2", "treatment_code"])

    lookup_keys = ["year", "treatment_code", "treatment", "treatment_group", "N_fertilizer_kg_ha",
                   "P2O5_fertilizer_kg_ha", "K2O_fertilizer_kg_ha", "organic_fertilizer_t_ha",
                   "N_source", "N_application_method", "N_application_time"]
    lookup = (merged.groupby(lookup_keys, dropna=False)
              .agg(n_obs=("year", "size"), dataset_id=("dataset_id", joined_unique)).reset_index())
    lookup["note"] = np.where(lookup["year"].eq(2019),
        "Treatment code retained from wide source file; fertilizer rates not embedded.", pd.NA)
    lookup = lookup.sort_values(["year", "treatment_code"])
    qa_counts = (merged.groupby(["year", "dataset_id", "source_file"], dropna=False)
                 .size().rename("n_rows").reset_index().sort_values(["year", "dataset_id"]))
    qa_missing = pd.DataFrame([{
        "total_rows": len(merged), "missing_year": merged["year"].isna().sum(),
        "missing_site": merged["site"].isna().sum(),
        "missing_treatment": merged["treatment_code"].isna().sum(),
        "missing_yield": merged["yield_kg_ha"].isna().sum(),
        "missing_N_rate": merged["N_fertilizer_kg_ha"].isna().sum(),
    }])
    descriptions = {"dataset_id": "Harmonized dataset identifier.", "source_file": "Original source file name.",
                    "source_sheet": "Original sheet or data source.", "year": "Trial or observation year.",
                    "season": "Cropping season where available.", "site": "Combined site identifier.",
                    "treatment_code": "Treatment code from source data.",
                    "yield_kg_ha": "Reported or moisture-corrected grain yield, kg ha-1.",
                    "yield_t_ha": "Reported or moisture-corrected grain yield, t ha-1.",
                    "notes": "Processing notes."}
    dictionary = pd.DataFrame({"variable": CAROB_COLS})
    dictionary["description"] = dictionary["variable"].map(descriptions).fillna("Carob-like harmonized variable.")

    OUT.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT / "merged_maize_trials_carob_like.csv", index=False)
    summary.to_csv(OUT / "summary_maize_by_year_site_treatment.csv", index=False)

    workbook = OUT / "maize_trials_merged_carob_summary.xlsx"
    temporary_workbook = OUT / ".maize_trials_merged_carob_summary.tmp.xlsx"
    excel_sheets = {
        "merged_carob": sanitize_excel_frame(merged),
        "summary_year_site_treatment": sanitize_excel_frame(summary),
        "treatment_lookup": sanitize_excel_frame(lookup),
        "qa_counts": sanitize_excel_frame(qa_counts),
        "qa_missing": sanitize_excel_frame(qa_missing),
        "data_dictionary": sanitize_excel_frame(dictionary),
    }

    try:
        with pd.ExcelWriter(temporary_workbook, engine="openpyxl") as writer:
            # Keep the workbook valid if a later sheet raises an exception,
            # preventing openpyxl from masking the original error.
            pd.DataFrame({"status": ["building"]}).to_excel(
                writer, sheet_name="__building__", index=False
            )
            for sheet_name, frame in excel_sheets.items():
                frame.to_excel(writer, sheet_name=sheet_name, index=False)
            del writer.book["__building__"]

        temporary_workbook.replace(workbook)
    except Exception:  # noqa: BLE001 -- clean temporary output before reraising
        temporary_workbook.unlink(missing_ok=True)
        raise

    print(f"Merge completed: {len(merged)} rows; summary: {len(summary)} rows.")
    print(f"Outputs saved under: {OUT}")


if __name__ == "__main__":
    main()