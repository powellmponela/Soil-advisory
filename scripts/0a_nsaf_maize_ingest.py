from __future__ import annotations

r"""
NSAF maize Stage 1: ingest, realign and extract key analytical variables.

Project root
------------
D:\dss\SOIL ADVISORY

Run
---
python .\scripts\0a_nsaf_maize_ingest.py

Purpose
-------
Read the original NSAF maize source files, realign variables that differ across
workbooks, reshape the 2019 wide treatment blocks, and create one long-format
harmonised table for downstream agronomic analysis.

The main harmonised table contains only the analytical keys:
    year, study, dataset_type, district, site, latitude, longitude,
    variety, treatment_code, treatment, adjusted_yield_kg_ha

Important
---------
- 2017 yield is retained as recorded; no moisture adjustment is applied.
- 2018 and 2019 use recorded grain yield and measured grain moisture.
- Dry yield is calculated first, then converted to 14% grain moisture.
- Final analytical fields are: grain_moisture_pct, recorded_yield_kg_ha, dry_yield_kg_ha, yield_14pct_kg_ha.
- No decimal-place or agronomic value correction is guessed.
- Obvious 2019 source-field displacement between grain moisture and corrected yield is realigned using physical field ranges and is logged in provenance/QC.
- General yield QC: 1-2 records >15,000 kg/ha within a study-year-site are excluded individually; 3 or more trigger exclusion of the whole site.
- Soil-background QC: N0-P0-K0 records with yield = 0 or >8,500 kg/ha are excluded individually.
- The 8,500 kg/ha ceiling applies only to the soil-background treatment, not fertilised treatments.
- Excluded records/sites are retained in provenance/QC for traceability.
- 2019 is rebuilt from the raw postharvest workbook; maize_demo_2019.xlsx is
  intentionally not used because its exported columns are misaligned.
"""

from pathlib import Path
import argparse
import re

import numpy as np
import pandas as pd

FILE_2017 = "maize_trials_2017.xlsx"
FILE_2018 = "maize_trials-2018.csv"
FILE_2018_DEMO = "maize_demo-2018.csv"
FILE_2019 = (
    "Maize_postharvest_2019 - all versions - labels - "
    "2020-01-23-04-01-40.xlsx"
)

MAIN_NAME = "nsaf_maize_key_variables.csv"
PROVENANCE_NAME = "nsaf_maize_provenance.csv"
MAPPING_NAME = "nsaf_maize_column_mapping.csv"

TARGET_GRAIN_MOISTURE_PCT = 14.0

MAIN_COLUMNS = [
    "year",
    "study",
    "dataset_type",
    "district",
    "site",
    "latitude",
    "longitude",
    "variety",
    "variety_group",
    "treatment_code",
    "source_treatment_label",
    "treatment",
    "treatment_role",
    "N_rate_kg_ha",
    "P_rate_kg_ha",
    "K_rate_kg_ha",
    "grain_moisture_pct",
    "recorded_yield_kg_ha",
    "dry_yield_kg_ha",
    "yield_14pct_kg_ha",
]

TREATMENT_2017 = {
    "1": "N0-P0-K0",
    "2": "N0-P60-K40",
    "3": "N120-P0-K40",
    "4": "N120-P60-K0",
    "5": "N60-P60-K40",
    "6": "N120-P60-K40",
    "7": "N180-P60-K40",
    "8": "N210-P60-K40",
    "9": "N120-P60-K40 + micronutrients",
    "10": "N120-P60-K40 + K/S treatment",
}

TREATMENT_2018 = {
    "1": "N120-P60-K40 urea split",
    "2": "N120-P60-K40 PCU basal",
    "3": "N60-P60-K40 PCU basal",
    "4": "N78-P60-K40 UDP basal",
    "5": "FYM 6 t/ha + N60-P60-K40",
    "6": "N120-P0-K40",
    "7": "N0-P60-K40",
    "8": "N0-P0-K0",
    "9": "N120-P60-K40 urea split at V6/V10",
}

TREATMENT_2019 = {
    "T1": "N0-P0-K0",
    "T2": "N0-P60-K40",
    "T3": "N120-P0-K40",
    "T4": "N120-P60-K0",
    "T5": "N60-P60-K40",
    "T6": "N120-P60-K40",
    "T7": "N180-P60-K40",
    "T8": "N210-P60-K40",
    "T9": "N120-P60-K40 at V8",
    "T10": "N120-P60-K40 at V6/V10",
    "A1": "Hybrid N120-P60-K40",
    "A2": "Hybrid FYM 6 t/ha + N120-P60-K40",
    "A3": "Hybrid Zn + N120-P60-K40",
    "A4": "Hybrid PCU N60-P60-K40",
    "A5": "Hybrid UDP N78-P60-K40",
    "B1": "OPV N120-P60-K40",
    "B2": "OPV FYM 6 t/ha + N120-P60-K40",
    "B3": "OPV Zn + N120-P60-K40",
    "B4": "OPV PCU N60-P60-K40",
    "B5": "OPV UDP N78-P60-K40",
}

CODES_2019 = [
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10",
    "A1", "A2", "A3", "A4", "A5",
    "B1", "B2", "B3", "B4", "B5",
]

DISTRICT_NORMALIZATION = {
    "surket": "Surkhet",
    "surkhet": "Surkhet",
    "dang": "Dang",
    "palpa": "Palpa",
    "kavre": "Kavre",
    "doti": "Doti",
    "nuwakot": "Nuwakot",
    "makwanpur": "Makwanpur",
    "salyan": "Salyan",
    "chitwan": "Chitwan",
}

SITE_COLUMN_2019 = {
    "Surkhet": "Surket",
    "Dang": "Dang",
    "Palpa": "Palpa",
    "Kavre": "Kavre",
    "Doti": "Doti",
    "Nuwakot": "Nuwakot",
    "Makwanpur": "Makwanpur",
    "Salyan": "Salyan",
    "Chitwan": "Chitwan",
}


def text_or_na(value):
    if pd.isna(value):
        return pd.NA
    value = str(value).strip()
    if not value or value.lower() in {"nan", "none", "null"}:
        return pd.NA
    return value


def numeric(value):
    return pd.to_numeric(value, errors="coerce")


def realign_2019_moisture_adjusted(raw_yield, moisture_value, adjusted_value):
    """
    Realign only obvious source-field displacement in 2019 postharvest blocks.

    The Kobo export has two observed cases where the value stored under the
    grain-moisture column is clearly a kg/ha corrected yield:

    1) moisture > 100 and adjusted yield is a plausible moisture percentage
       (0-100): swap the two fields.
    2) moisture > 100 and adjusted yield is missing: move the moisture-column
       value to adjusted yield and leave moisture missing.

    This does NOT repair decimal points, recalculate yield from moisture, or
    change other questionable source values. Those remain QC flags.
    """
    raw = numeric(raw_yield)
    moisture = numeric(moisture_value)
    adjusted = numeric(adjusted_value)

    aligned_moisture = moisture
    aligned_adjusted = adjusted
    action = pd.NA

    if pd.notna(moisture) and moisture > 100:
        if pd.notna(adjusted) and 0 < adjusted <= 100:
            aligned_moisture = adjusted
            aligned_adjusted = moisture
            action = "swap_moisture_and_adjusted_yield"
        elif pd.isna(adjusted):
            aligned_moisture = np.nan
            aligned_adjusted = moisture
            action = "move_adjusted_yield_from_moisture_column"

    return raw, aligned_moisture, aligned_adjusted, action


def normalize_code(value):
    if pd.isna(value):
        return pd.NA
    try:
        f = float(value)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass
    return str(value).strip()


def normalize_district(value):
    value = text_or_na(value)
    if pd.isna(value):
        return pd.NA
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    return DISTRICT_NORMALIZATION.get(key, str(value).strip())


def clean_site(value):
    value = text_or_na(value)
    if pd.isna(value):
        return pd.NA
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_colname(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def resolve_maize_dir(root: Path) -> Path:
    candidates = [
        root / "Data" / "NSAF Crops Trial Data" / "Maize",
        root / "NSAF Crops Trial Data" / "Maize",
        root / "Data" / "NSAF_Crops_Trial_Data" / "Maize",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Could not locate NSAF maize directory. Checked:\n"
        + "\n".join(str(p) for p in candidates)
    )


def require_columns(df, cols, source):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{source}: missing required columns: {missing}")


def map_row(mapping, year, file, source_variable, aligned_variable, note=""):
    mapping.append({
        "year": year,
        "source_file": file,
        "source_variable": source_variable,
        "aligned_variable": aligned_variable,
        "note": note,
    })


def make_record(**kwargs):
    return kwargs


def ingest_2017(path: Path, mapping: list[dict]) -> list[dict]:
    sheet = "maize_trials_2017"
    df = pd.read_excel(path, sheet_name=sheet)
    require_columns(
        df,
        ["District", "VDC", "treatment_code", "latitude", "longitude", "Yield_kg_ha"],
        path.name,
    )

    for src, dst in [
        ("District", "district"),
        ("VDC", "site"),
        ("treatment_code", "treatment_code"),
        ("latitude", "latitude"),
        ("longitude", "longitude"),
        ("Yield_kg_ha", "source_adjusted_yield"),
    ]:
        map_row(mapping, 2017, path.name, src, dst)

    records = []
    for i, row in df.iterrows():
        code = normalize_code(row.get("treatment_code"))
        records.append(make_record(
            year=2017,
            study="2017 core trial",
            dataset_type="trial",
            district=normalize_district(row.get("District")),
            site=clean_site(row.get("VDC")),
            latitude=numeric(row.get("latitude")),
            longitude=numeric(row.get("longitude")),
            variety=text_or_na(row.get("variety")),
            treatment_code=code,
            treatment=TREATMENT_2017.get(code, pd.NA),
            adjusted_yield_kg_ha=numeric(row.get("Yield_kg_ha")),
            source_adjusted_yield=numeric(row.get("Yield_kg_ha")),
            source_raw_grain_yield=numeric(row.get("grain_yield_kg_ha")),
            source_grain_moisture=numeric(row.get("moisture%")),
            aligned_grain_moisture=numeric(row.get("moisture%")),
            alignment_action=pd.NA,
            source_yield_column="Yield_kg_ha",
            source_file=path.name,
            source_sheet=sheet,
            source_row=int(i) + 2,
        ))
    return records


def ingest_2018(path: Path, mapping: list[dict]) -> list[dict]:
    df = pd.read_csv(path)
    require_columns(
        df,
        ["District", "VDC", "treatment", "latitude", "longitude", "Yield_kg_ha"],
        path.name,
    )

    for src, dst in [
        ("District", "district"),
        ("VDC", "site"),
        ("treatment", "treatment_code"),
        ("latitude", "latitude"),
        ("longitude", "longitude"),
        ("Yield_kg_ha", "source_adjusted_yield"),
    ]:
        map_row(mapping, 2018, path.name, src, dst)

    records = []
    for i, row in df.iterrows():
        code = normalize_code(row.get("treatment"))
        records.append(make_record(
            year=2018,
            study="2018 N source, timing and FYM trial",
            dataset_type="trial",
            district=normalize_district(row.get("District")),
            site=clean_site(row.get("VDC")),
            latitude=numeric(row.get("latitude")),
            longitude=numeric(row.get("longitude")),
            variety=pd.NA,
            treatment_code=code,
            treatment=TREATMENT_2018.get(code, pd.NA),
            adjusted_yield_kg_ha=numeric(row.get("Yield_kg_ha")),
            source_adjusted_yield=numeric(row.get("Yield_kg_ha")),
            source_raw_grain_yield=numeric(row.get("grain_yield_kg_ha")),
            source_grain_moisture=numeric(row.get("moisture%")),
            aligned_grain_moisture=numeric(row.get("moisture%")),
            alignment_action=pd.NA,
            source_yield_column="Yield_kg_ha",
            source_file=path.name,
            source_sheet="CSV",
            source_row=int(i) + 2,
        ))
    return records


def ingest_2018_demo(path: Path, mapping: list[dict]) -> list[dict]:
    """Ingest maize_demo-2018.csv as a separate 2018 Demo dataset."""
    df = pd.read_csv(path)
    require_columns(df, [
        "District", "VDC", "Farmers's name", "Demo",
        "N_kg_ha", "P2O5_kg_ha", "K2O_kg_ha", "variety",
        "latitude", "longitude", "grain_yield_kg_ha",
        "moisture%", "Yield_kg_ha",
    ], path.name)

    records = []
    for i, row in df.iterrows():
        code = text_or_na(row.get("Demo"))
        variety = text_or_na(row.get("variety"))
        if pd.notna(variety) and str(variety).lower().startswith("hybrid"):
            vg = "Hybrid"
        elif pd.notna(variety) and str(variety).lower().startswith("opv"):
            vg = "OPV"
        elif pd.notna(variety) and "farmer" in str(variety).lower():
            vg = "Farmers seed"
        else:
            vg = variety

        n = numeric(row.get("N_kg_ha"))
        p = numeric(row.get("P2O5_kg_ha"))
        k = numeric(row.get("K2O_kg_ha"))
        trt = f"{variety}: N{int(n)}-P{int(p)}-K{int(k)}"

        records.append(make_record(
            year=2018, study="2018 maize demo", dataset_type="Demo",
            district=normalize_district(row.get("District")),
            site=clean_site(row.get("VDC")),
            farmer=text_or_na(row.get("Farmers's name")),
            latitude=numeric(row.get("latitude")),
            longitude=numeric(row.get("longitude")),
            variety=variety, variety_group=vg,
            treatment_code=code, source_treatment_label=code,
            treatment=trt,
            treatment_role=f"demo_{str(code).lower()}",
            N_rate_kg_ha=n, P_rate_kg_ha=p, K_rate_kg_ha=k,
            adjusted_yield_kg_ha=numeric(row.get("Yield_kg_ha")),
            source_adjusted_yield=numeric(row.get("Yield_kg_ha")),
            source_raw_grain_yield=numeric(row.get("grain_yield_kg_ha")),
            source_grain_moisture=numeric(row.get("moisture%")),
            aligned_grain_moisture=numeric(row.get("moisture%")),
            alignment_action=pd.NA,
            source_yield_column="Yield_kg_ha",
            source_file=path.name, source_sheet="CSV", source_row=int(i)+2,
            barcode=text_or_na(row.get("barcode")),
        ))
    return records


def block_columns(columns: list[str], code: str) -> list[str]:
    start = columns.index(code)
    later = [columns.index(c) for c in CODES_2019 if c in columns and columns.index(c) > start]
    end = min(later) if later else len(columns)
    return columns[start + 1:end]


def find_one(block: list[str], predicate, label: str, code: str) -> str | None:
    candidates = [c for c in block if predicate(normalize_colname(c))]
    if not candidates:
        return None
    if len(candidates) > 1:
        raise ValueError(f"2019 {code}: multiple {label} columns found: {candidates}")
    return candidates[0]


def find_2019_variables(columns: list[str], code: str):
    block = block_columns(columns, code)

    adjusted = find_one(
        block,
        lambda n: "moisturecorrectedgrainyieldkgha" in n,
        "adjusted-yield",
        code,
    )
    raw_yield = find_one(
        block,
        lambda n: (
            "grainyieldkgha" in n
            and "moisturecorrected" not in n
            and "straw" not in n
        ),
        "raw grain-yield",
        code,
    )
    moisture = find_one(
        block,
        lambda n: "grainmoisture" in n and "corrected" not in n,
        "grain-moisture",
        code,
    )

    return adjusted, raw_yield, moisture


def site_from_2019(row: pd.Series, district):
    if pd.isna(district):
        return pd.NA
    col = SITE_COLUMN_2019.get(str(district))
    if col and col in row.index:
        site = clean_site(row.get(col))
        if pd.notna(site):
            return site
    # Keep the record identifiable if a site field is absent.
    return clean_site(row.get("Farmer's name"))


def ingest_2019(path: Path, mapping: list[dict]) -> list[dict]:
    """
    Ingest the dedicated 2019 sheets:
        - "Trial 2019" for T1-T10
        - "Demo 2019" for A1-A5 and B1-B5

    Yield fields are taken directly from the source sheets:
        recorded_yield_kg_ha <- Grain yield (kg/ha)
        grain_moisture_pct   <- Grain moisture (%)
        yield_14pct_kg_ha    <- moisture corrected_grain yield (kg/ha)

    The source moisture-corrected yield is used as reported. It is not
    recalculated during ingest.

    Obvious 2019 moisture/corrected-yield field displacement is realigned
    conservatively before the analytical fields are created.
    """
    records = []

    sheet_codes = {
        "Trial 2019": [f"T{i}" for i in range(1, 11)],
        "Demo 2019": [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)],
    }

    for sheet, codes in sheet_codes.items():
        df = pd.read_excel(path, sheet_name=sheet)
        require_columns(df, ["District", "Trial/Demo"], f"{path.name}:{sheet}")
        columns = list(df.columns)

        for code in codes:
            if code not in columns:
                raise ValueError(f"{path.name}:{sheet}: missing treatment block {code}")

            # Use the treatment block boundaries within this sheet only.
            start_i = columns.index(code)
            later = [
                columns.index(c)
                for c in codes
                if c in columns and columns.index(c) > start_i
            ]
            end_i = min(later) if later else len(columns)
            block = columns[start_i + 1:end_i]

            raw_col = find_one(
                block,
                lambda n: (
                    "grainyieldkgha" in n
                    and "moisturecorrected" not in n
                    and "straw" not in n
                ),
                "raw grain-yield",
                code,
            )
            moisture_col = find_one(
                block,
                lambda n: "grainmoisture" in n and "corrected" not in n,
                "grain-moisture",
                code,
            )
            adjusted_col = find_one(
                block,
                lambda n: "moisturecorrectedgrainyieldkgha" in n,
                "moisture-corrected grain yield",
                code,
            )

            lat_col = f"_{code}_latitude"
            lon_col = f"_{code}_longitude"

            if raw_col is None:
                raise ValueError(f"2019 {sheet} {code}: grain-yield column not found")
            if moisture_col is None:
                raise ValueError(f"2019 {sheet} {code}: grain-moisture column not found")
            if adjusted_col is None:
                raise ValueError(f"2019 {sheet} {code}: moisture-corrected yield column not found")

            require_columns(
                df,
                [lat_col, lon_col, raw_col, moisture_col, adjusted_col],
                f"{path.name}:{sheet}:{code}",
            )

            for src, dst in [
                (lat_col, "latitude"),
                (lon_col, "longitude"),
                (raw_col, "recorded_yield_kg_ha"),
                (moisture_col, "grain_moisture_pct"),
                (adjusted_col, "yield_14pct_kg_ha"),
            ]:
                map_row(mapping, 2019, path.name, src, dst, f"{sheet} treatment block {code}")

            if code.startswith("T"):
                study = "2019 T1-T10 core trial"
                dataset_type = "Trial"
                variety = "All maize"
                allowed = df["Trial/Demo"].astype(str).str.contains("Trial", case=False, na=False)
            elif code.startswith("A"):
                study = "2019 Hybrid strategy block"
                dataset_type = "Demo"
                variety = "Hybrid"
                allowed = df["Trial/Demo"].astype(str).str.contains("Demo", case=False, na=False)
            else:
                study = "2019 OPV strategy block"
                dataset_type = "Demo"
                variety = "OPV"
                allowed = df["Trial/Demo"].astype(str).str.contains("Demo", case=False, na=False)

            present = (
                df[code].notna()
                | pd.to_numeric(df[raw_col], errors="coerce").notna()
                | pd.to_numeric(df[adjusted_col], errors="coerce").notna()
            )
            subset = df.loc[allowed & present].copy()

            for i, row in subset.iterrows():
                district = normalize_district(row.get("District"))

                source_raw = numeric(row.get(raw_col))
                source_moisture = numeric(row.get(moisture_col))
                source_adjusted = numeric(row.get(adjusted_col))

                (
                    aligned_raw,
                    aligned_moisture,
                    aligned_adjusted,
                    alignment_action,
                ) = realign_2019_moisture_adjusted(
                    source_raw,
                    source_moisture,
                    source_adjusted,
                )

                records.append(make_record(
                    year=2019,
                    study=study,
                    dataset_type=dataset_type,
                    district=district,
                    site=site_from_2019(row, district),
                    latitude=numeric(row.get(lat_col)),
                    longitude=numeric(row.get(lon_col)),
                    variety=variety,
                    treatment_code=code,
                    treatment=TREATMENT_2019[code],

                    # Internal ingest fields used to create the three
                    # final analytical yield columns.
                    adjusted_yield_kg_ha=aligned_adjusted,
                    source_adjusted_yield=aligned_adjusted,
                    source_raw_grain_yield=aligned_raw,
                    source_grain_moisture=aligned_moisture,
                    aligned_grain_moisture=aligned_moisture,
                    alignment_action=alignment_action,

                    source_yield_column=adjusted_col,
                    source_file=path.name,
                    source_sheet=sheet,
                    source_row=int(i) + 2,
                ))

    return records



def standardize_yield_to_14pct(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build yield from recorded grain yield and measured grain moisture.

    Final analytical fields
    -----------------------
    grain_moisture_pct
    recorded_yield_kg_ha
    dry_yield_kg_ha
    yield_14pct_kg_ha

    Calculation
    -----------
    Dry matter yield:
        Ydry = Yrecorded * (100 - MC) / 100

    Yield at 14% moisture:
        Y14 = Ydry / 0.86

    Equivalent direct form:
        Y14 = Yrecorded * (100 - MC) / 86

    Year rules
    ----------
    2017:
        No reliable grain-moisture field is used. Retain the recorded yield
        as the analytical yield and leave dry_yield_kg_ha missing.

    2018 and 2019:
        Use the recorded grain yield and measured grain moisture from the
        source data to calculate dry matter yield and then yield at 14% MC.
        The source moisture-corrected yield is not used to calculate Y14.
    """
    out = df.copy()

    recorded = pd.to_numeric(
        out["source_raw_grain_yield"],
        errors="coerce",
    )
    mc = pd.to_numeric(
        out["aligned_grain_moisture"],
        errors="coerce",
    )
    reported = pd.to_numeric(
        out["adjusted_yield_kg_ha"],
        errors="coerce",
    )

    out["grain_moisture_pct"] = np.nan
    out["recorded_yield_kg_ha"] = np.nan
    out["dry_yield_kg_ha"] = np.nan
    out["yield_14pct_kg_ha"] = np.nan

    # 2017: no moisture adjustment; use reported yield as-is.
    m17 = out["year"].eq(2017)
    out.loc[m17, "recorded_yield_kg_ha"] = reported.loc[m17]
    out.loc[m17, "yield_14pct_kg_ha"] = reported.loc[m17]

    # 2018 and 2019: use recorded grain yield + measured MC.
    m1819 = out["year"].isin([2018, 2019])
    out.loc[m1819, "grain_moisture_pct"] = mc.loc[m1819]
    out.loc[m1819, "recorded_yield_kg_ha"] = recorded.loc[m1819]

    valid = (
        m1819
        & recorded.notna()
        & (recorded >= 0)
        & mc.notna()
        & (mc >= 0)
        & (mc < 100)
    )

    out.loc[valid, "dry_yield_kg_ha"] = (
        recorded.loc[valid]
        * (100.0 - mc.loc[valid])
        / 100.0
    )

    out.loc[valid, "yield_14pct_kg_ha"] = (
        out.loc[valid, "dry_yield_kg_ha"]
        / 0.86
    )

    return out



def add_analysis_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add canonical analysis labels once, upstream, for all downstream scripts."""
    out = df.copy()

    out["dataset_type"] = out["dataset_type"].replace({
        "trial": "Trial",
        "strategy": "Demo",
    })
    if "variety_group" not in out.columns:
        out["variety_group"] = out["variety"]
    else:
        out["variety_group"] = out["variety_group"].where(out["variety_group"].notna(), out["variety"])
    if "source_treatment_label" not in out.columns:
        out["source_treatment_label"] = out["treatment"]
    else:
        out["source_treatment_label"] = out["source_treatment_label"].where(out["source_treatment_label"].notna(), out["treatment"])

    def role(row):
        y = int(row["year"])
        c = str(row["treatment_code"]).strip().upper()

        if y == 2017:
            return {
                "1": "soil_background",
                "2": "n_omission",
                "3": "p_omission",
                "4": "k_omission",
                "5": "n_rate_60",
                "6": "government_recommendation",
                "7": "n_rate_180",
                "8": "n_rate_210",
                "9": "micronutrients",
                "10": "ks_treatment",
            }.get(c, "other")

        if y == 2018:
            if str(row.get("dataset_type", "")).strip().lower() == "demo":
                existing = row.get("treatment_role", pd.NA)
                return existing if pd.notna(existing) else f"demo_{c.lower()}"
            return {
                "1": "government_recommendation", "2": "pcu_full_n",
                "3": "pcu_half_n", "4": "udp_reduced_n",
                "5": "fym_half_n", "6": "p_omission",
                "7": "n_omission", "8": "soil_background",
                "9": "n_timing_v6_v10",
            }.get(c, "other")

        if y == 2019:
            return {
                "T1": "soil_background",
                "T2": "n_omission",
                "T3": "p_omission",
                "T4": "k_omission",
                "T5": "n_rate_60",
                "T6": "government_recommendation",
                "T7": "n_rate_180",
                "T8": "n_rate_210",
                "T9": "n_timing_v8",
                "T10": "n_timing_v6_v10",
                "A1": "demo_gr_hybrid",
                "A2": "demo_fym_hybrid",
                "A3": "demo_zn_hybrid",
                "A4": "demo_pcu_half_n_hybrid",
                "A5": "demo_udp_reduced_n_hybrid",
                "B1": "demo_gr_opv",
                "B2": "demo_fym_opv",
                "B3": "demo_zn_opv",
                "B4": "demo_pcu_half_n_opv",
                "B5": "demo_udp_reduced_n_opv",
            }.get(c, "other")

        return "other"

    out["treatment_role"] = out.apply(role, axis=1)

    def rates(text):
        m = re.search(r"N(\d+)-P(\d+)-K(\d+)", str(text))
        if not m:
            return pd.Series([np.nan, np.nan, np.nan])
        return pd.Series([float(m.group(1)), float(m.group(2)), float(m.group(3))])

    parsed = out["treatment"].apply(rates)
    parsed.columns = ["N_rate_kg_ha", "P_rate_kg_ha", "K_rate_kg_ha"]
    for col in parsed.columns:
        if col not in out.columns:
            out[col] = parsed[col]
        else:
            existing = pd.to_numeric(out[col], errors="coerce")
            out[col] = existing.where(existing.notna(), parsed[col])
    return out

def main():
    parser = argparse.ArgumentParser(description="Ingest and realign NSAF maize key variables")
    parser.add_argument(
        "--root",
        default=None,
        help="SOIL ADVISORY project root; defaults to the parent of scripts/",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    maize_dir = resolve_maize_dir(root)
    harmonised_dir = maize_dir / "harmonised"
    harmonised_dir.mkdir(parents=True, exist_ok=True)

    files = {
        2017: maize_dir / FILE_2017,
        2018: maize_dir / FILE_2018,
        2018.1: maize_dir / FILE_2018_DEMO,
        2019: maize_dir / FILE_2019,
    }
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required source files:\n" + "\n".join(missing))

    mapping = []
    records = []
    records.extend(ingest_2017(files[2017], mapping))
    records.extend(ingest_2018(files[2018], mapping))
    records.extend(ingest_2018_demo(files[2018.1], mapping))
    records.extend(ingest_2019(files[2019], mapping))

    full = pd.DataFrame(records)
    full = standardize_yield_to_14pct(full)
    full = full[
        full["treatment_code"].notna()
        & (
            full["yield_14pct_kg_ha"].notna()
            | full["latitude"].notna()
            | full["longitude"].notna()
        )
    ].copy()

    full = full.sort_values(
        ["year", "study", "district", "site", "treatment_code"],
        na_position="last",
    ).reset_index(drop=True)

    full = add_analysis_labels(full)
    main_data = full[MAIN_COLUMNS].copy()

    provenance = full[MAIN_COLUMNS].copy()

    mapping_df = pd.DataFrame(mapping).drop_duplicates().sort_values(
        ["year", "aligned_variable", "source_file", "source_variable"]
    )

    print("\nYIELD FIELDS")
    print("=" * 72)
    print(
        full.groupby("year")
        .agg(
            n=("yield_14pct_kg_ha", "count"),
            mean_recorded_yield_kg_ha=("recorded_yield_kg_ha", "mean"),
            mean_dry_yield_kg_ha=("dry_yield_kg_ha", "mean"),
            mean_yield_14pct_kg_ha=("yield_14pct_kg_ha", "mean"),
            n_with_mc=("grain_moisture_pct", "count"),
        )
        .reset_index()
        .to_string(index=False)
    )


    main_path = harmonised_dir / MAIN_NAME
    provenance_path = harmonised_dir / PROVENANCE_NAME
    mapping_path = harmonised_dir / MAPPING_NAME

    main_data.to_csv(main_path, index=False)

    demo_2018 = main_data.loc[(main_data["year"] == 2018) & (main_data["dataset_type"] == "Demo")].copy()
    trial_2019 = main_data.loc[(main_data["year"] == 2019) & (main_data["dataset_type"] == "Trial")].copy()
    demo_2019 = main_data.loc[(main_data["year"] == 2019) & (main_data["dataset_type"] == "Demo")].copy()

    demo_2018.to_csv(harmonised_dir / "nsaf_maize_2018_demo.csv", index=False)
    trial_2019.to_csv(harmonised_dir / "nsaf_maize_2019_trial_T1_T10.csv", index=False)
    demo_2019.to_csv(harmonised_dir / "nsaf_maize_2019_demo_Hybrid_OPV.csv", index=False)

    provenance.to_csv(provenance_path, index=False)
    mapping_df.to_csv(mapping_path, index=False)

    print("=" * 96)
    print("NSAF MAIZE STAGE 1 - INGEST / REALIGN")
    print("=" * 96)
    print(f"Project root:     {root}")
    print(f"Raw maize data:   {maize_dir}")
    print(f"Harmonised data:  {harmonised_dir}")
    print()
    print("Main analytical variables:")
    print("  " + ", ".join(MAIN_COLUMNS))
    print()
    print("Harmonised outputs contain the agreed analytical variables only.")
    print()

    summary = (
        main_data.groupby(["year", "study", "dataset_type"], dropna=False)
        .agg(
            observations=("treatment_code", "size"),
            districts=("district", "nunique"),
            sites=("site", "nunique"),
            treatments=("treatment_code", "nunique"),
            yield_records=("yield_14pct_kg_ha", "count"),
        )
        .reset_index()
    )
    print(summary.to_string(index=False))
    print()
    print(f"Main data:   {main_path}")
    print(f"Provenance:  {provenance_path}")
    print(f"Mapping:     {mapping_path}")


if __name__ == "__main__":
    main()
