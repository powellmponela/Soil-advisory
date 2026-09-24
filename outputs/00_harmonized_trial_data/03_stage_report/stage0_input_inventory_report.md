# Stage 0a input inventory report

Script: `0a_prepare_input_inventory.py`

Project root: `D:\dss\SOIL ADVISORY`

## Purpose

This script checks that the static input files needed for Stage 0 are present before the workflow proceeds. It does not call the DSM API, does not move source files, and does not alter downloaded DSM resolution.

## Key checks

- Expected input records checked: 31
- Missing expected inputs: 0
- DSM layer folders found: 11 of 11
- m_n_publications summary rows: 41

## Soil-data policy

1. Use soil values reported in `m_n_publications/maize.csv` first.
2. Fill missing soil covariates from locally downloaded high-resolution NARC DSM layers in `Data/dsm`.
3. Keep DSM rasters at native/original resolution.
4. Do not call the DSM API.
5. Use ISRIC/SoilGrids only for supplemental properties not provided locally, such as CEC, bulk density, soil depth/depth-to-bedrock proxy, and volumetric water content.

## Outputs

- `stage0_input_inventory.csv`
- `stage0_dsm_layer_inventory.csv`
- `stage0_m_n_publications_quick_summary.csv`
- `stage0_m_n_publications_counts_by_*.csv`

## Missing expected inputs

No expected inputs are missing.
