# Run the NSAF Stage 1-6 workflow in VS Code

Open this folder itself as the VS Code workspace.

## 1. Select Python

Use `Ctrl+Shift+P` -> `Python: Select Interpreter`.

## 2. Install the small descriptive-workflow dependency set

From the VS Code terminal:

```powershell
python -m pip install -r requirements_nsaf_descriptives.txt
```

## 3. Run the study-year audit first

Use:

`Terminal -> Run Task -> NSAF: audit study-year availability`

Choose the NSAF Excel workbook when prompted by entering its full local path.

The key output is:

`output_descriptives/study_year_stage_availability.csv`

Review this before interpreting Stage 1-6 because it shows which treatments/stages exist in each study and each year.

## 4. Run all six stages

Use:

`Terminal -> Run Task -> NSAF: run stages 1-6 by study-year`

Default retention threshold is 0.95.

Equivalent terminal command:

```powershell
python .\run_all.py "FULL_PATH\NSAF_spatial_trial_and_response_contrast_datasets.xlsx" --out ".\output_descriptives" --retention 0.95
```

## Primary analytical outputs

For each stage use these first:

- `*_trial_site.csv`
- `*_study_year.csv`
- `*_study_year_district.csv`
- `*_study_year_district_site.csv`

Do not start with the pooled district-across-study summaries.

The analytical order is:

`study -> year -> district -> site/trial`

Treatment contrasts are created within `trial_year_id` before any summaries are produced.

## Stage interpretation

1. N0-P0-K0 = no-input farmer baseline
2. N0-P-K = agronomic N-response baseline
3. FYM + N60 = Nepal farmer-practice proxy
4. N120-P-K = government recommendation
5. N-rate response = target can move down, stay at 120, or move up
6. Timing / UDP / PCU / nutrient-support alternatives = efficiency adjustments around the target

All current N-demand/target outputs remain in kg N/ha. District crop area is added later.
