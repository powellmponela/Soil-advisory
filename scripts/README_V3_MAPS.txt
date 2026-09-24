NSAF STAGE 1-6 V3: MAPS + INDIVIDUAL-SITE DISTRIBUTIONS
========================================================

Copy the .py files into:

D:\dss\SOIL ADVISORY\scripts

Run from project root:

cd "D:\dss\SOIL ADVISORY"
python .\scripts\run_nsaf_stage1_6.py


SEQUENCE
--------

0c_nsaf_data_legacy.py
    Existing legacy loader/harmoniser.

1a_nsaf_stage1_6_descriptives.py
    Corrected Stage 1-6 site and study-year descriptives.

1b_nsaf_stage1_6_maps_figures.py
    Maps and figures preserving individual site observations.


MAP OUTPUTS
-----------

D:\dss\SOIL ADVISORY\outputs\maps\stage1_6

For each study x year x variety x treatment, available maps include:

- yield kg/ha
- AE-N where scientifically applicable
- mineral-N productivity
- yield retention relative to the government benchmark
- estimated mineral-N saving where applicable

The script also creates Stage 5 target maps for:

- target N kg/ha
- target shift from government N120
- potential N saving kg/ha
- potential additional N kg/ha


DISTRIBUTION FIGURES
--------------------

D:\dss\SOIL ADVISORY\outputs\figures\stage1_6

Each study x year x variety receives separate distribution figures.
Boxplots summarise the distribution while the overlaid points preserve every
individual site observation.

Metrics include:

- yield
- AE-N
- mineral-N productivity
- yield retention
- estimated N saving


COORDINATES
-----------

The script first looks for coordinates in the Stage 1-6 output.

If absent, it searches existing project outputs and prioritises:

1. merged_maize_trials_carob_like.csv
2. maize_cimmyt_plot_results.csv
3. maize_2019_demo_plot_results.csv
4. external_fp_validation_results.csv

No coordinates are invented.

If a readable Nepal/admin boundary already exists somewhere in the project,
the script attempts to use it. Otherwise point maps are produced without
administrative boundaries.


IMPORTANT
---------

These are measured-trial-site maps only.

No DSM interpolation/extrapolation is used at this stage.

No district maize-area multiplication is used at this stage.

N saving means lower mineral-N input with retained yield, not measured N loss.
