# NSAF Nepal maize: Stage 1-6 descriptive decision ladder

## Purpose

These scripts use `Response_Contrast_Table` from
`NSAF_spatial_trial_and_response_contrast_datasets.xlsx`.

The analytical unit remains the trial-year/site. The scripts reconstruct treatment-level
yields from the benchmark and comparator sides of the paired contrast table, then create
trial-site and district summaries.

This is intentionally **not** a one-way intensification sequence. Each level is a reference
from which the fertilizer target may move upward, downward, or remain unchanged.

No district crop-area scaling is applied. All fertilizer targets and savings are in kg N/ha.
No DSM interpolation/extrapolation is applied at this stage.


## Mandatory analytical unit: every study and every year

All six stages are estimated **within each study and within each year** before any cross-study
or cross-year summary is made.

The hierarchy is:

`study -> year -> district -> site/trial`

The treatment contrast itself is calculated at the `trial_year_id` level. This prevents a
treatment yield from one study or year being compared with a benchmark yield from another.

Primary outputs from every stage are now:

- `*_trial_site.csv`
- `*_study_year.csv`
- `*_study_year_district.csv`
- `*_study_year_district_site.csv`

Secondary outputs are also written for later overview work:

- `*_study_all_years.csv`
- `*_district_year_across_studies.csv`

The secondary files must not be used to reconstruct treatment contrasts. They are summaries
of contrasts already calculated within study-year units.

A study-year is retained even if only one of the six stages is available. Therefore the
workflow does not require every study to contain every treatment. Each stage is calculated
only where the required treatments occur in the same trial-year.


## Stage narrative

### Stage 1 - N0-P0-K0: no-input farmer baseline

Question:
What yield is obtained when the farmer applies no N, P or K?

Primary output:
- yield_000_kg_ha

Interpretation:
This is the practical no-fertilizer farmer starting point and the yield floor. It is not the
clean comparator for N agronomic efficiency because P and K may also limit yield.

### Stage 2 - N0-P60-K40: N-response baseline

Question:
What yield can the site support when P and K are supplied but mineral N is withheld?

Primary outputs:
- yield_0PK_kg_ha
- PK_supported_gain_kg_ha = Y(0-P-K) - Y(0-0-0)

Interpretation:
This is the preferred agronomic baseline for isolating N response and estimating AE-N.

### Stage 3 - FYM + N60: farmer-practice proxy

Question:
Can a manure-based system with 60 kg mineral N/ha maintain useful yield, and how close is it
to the government N120 benchmark?

Primary outputs:
- yield_FYM_N60_kg_ha
- gain_vs_0PK_kg_ha
- PFP_mineral_N_kg_grain_per_kg_N
- retention_vs_govt
- estimated_N_saving_if_retained_kg_ha

Interpretation:
FYM + N60 is treated as a Nepal farmer-practice proxy, not as a pure mineral-N rate treatment.
The script therefore does not interpret its gain over N0-P-K as a clean AE-N estimate because
FYM also supplies nutrients. A 60 kg N/ha reduction is counted only when yield retains the
chosen fraction of the N120 benchmark (default 95%).

### Stage 4 - N120-P60-K40: government recommendation

Question:
What does the government recommendation add above the N0-P-K baseline, and does moving from
FYM + N60 to N120 produce enough additional yield to justify the extra 60 kg mineral N/ha?

Primary outputs:
- yield_govt_N120_kg_ha
- N_response_vs_0PK_kg_ha
- AE_N_kg_grain_per_kg_N
- PFP_N_kg_grain_per_kg_N
- package_gain_vs_000_kg_ha
- marginal_grain_per_extra_mineral_N_vs_FYM
- downward_shift_candidate_kg_N_ha

Interpretation:
N0-P-K is the clean comparator for the N120 response. N0-P0-K0 is retained as the practical
farmer no-input comparator. FYM + N60 is used to test whether the government N target can move
downward, but that comparison is a system comparison rather than a pure N-rate contrast.

### Stage 5 - N-rate target adjustment: move down, hold, or move up

Question:
Where does N120 lie on the local response curve, and what is the lowest tested N rate that
retains an acceptable share of the best observed yield?

Rates:
0, 60, 120, 180, 210 kg N/ha with P and K balanced where those treatments are available.

Decision rule:
For each trial-year, find the observed maximum yield and select the lowest available N rate
with yield >= retention threshold x observed maximum yield. Default threshold = 0.95.

Primary outputs:
- target_N_kg_ha
- target_shift_vs_govt_kg_N_ha
- N_saving_vs_govt_kg_ha
- N_increase_vs_govt_kg_ha
- AE_N60, AE_N120, AE_N180, AE_N210 where available

Interpretation:
Negative target shift = evidence to move below 120.
Zero = retain 120.
Positive = evidence that the tested yield target may require more than 120.

This is target-setting from NSAF evidence, not a claim that every farm should receive the
selected discrete rate.

### Stage 6 - efficiency alternatives around the target

Question:
Can timing, placement, controlled-release fertilizer, or nutrient support maintain/increase
yield and NUE at the same or lower mineral-N rate?

Alternatives currently classified:
- N120 at V6/V10
- N120 at V8
- Zn support
- K/S support
- UDP N78 and UDP N120
- PCU N60 and PCU N120

Primary outputs:
- yield_difference_vs_govt_kg_ha
- yield_retention_vs_govt
- candidate_N_reduction_kg_ha
- estimated_N_saving_if_retained_kg_ha
- PFP-N and delta PFP-N
- AE-N and delta AE-N where N0-P-K exists

Interpretation:
Reduced-N technologies produce a candidate N saving only if their yield meets the retention
criterion. Same-N technologies are evaluated mainly for yield and NUE improvement.

"N saving" means reduced mineral-N input while maintaining the specified yield criterion.
It must not be described as measured N-loss reduction because the NSAF yield trials did not
directly measure N losses.

## Running

Run all six stages:

```bash
python run_all.py NSAF_spatial_trial_and_response_contrast_datasets.xlsx --out output_descriptives --retention 0.95
```

Or run one stage:

```bash
python 05_stage5_N_rate_up_down_target.py NSAF_spatial_trial_and_response_contrast_datasets.xlsx --out output_descriptives
```

## Outputs

Each stage writes:
- `*_trial_site.csv`
- `*_study_year.csv`
- `*_study_year_district.csv`
- `*_study_year_district_site.csv`
- `*_study_all_years.csv`
- `*_district_year_across_studies.csv`

The first four files are the primary study-year outputs. Cross-study or cross-year summaries
are secondary and should not be used to calculate stage contrasts.

Stage 6 also writes:
- `stage6_by_alternative_study_year_district.csv`

These outputs are ready for the next mapping step. District crop area can later be joined to
convert kg N/ha into tonnes of district fertilizer demand or tonnes of potential N saving.
