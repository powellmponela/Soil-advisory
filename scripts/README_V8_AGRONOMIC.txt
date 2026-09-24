NSAF STAGE 1-6 V8 - AGRONOMIC TERMINOLOGY
=========================================

Copy these files into:

D:\dss\SOIL ADVISORY\scripts

Files:
1a_nsaf_stage1_6_descriptives.py
1b_nsaf_stage1_6_maps_figures.py
run_nsaf_stage1_6.py


EXISTING SCRIPT RETAINED
------------------------

0c_nsaf_data_legacy.py


RUN
---

From:

D:\dss\SOIL ADVISORY

run:

python .\scripts\run_nsaf_stage1_6.py


AGRonomic terminology
---------------------

The workflow now uses:

- yield
- yield response
- relative yield (%)
- agronomic efficiency of N (AE-N)
- partial factor productivity of N (PFP-N)
- N rate
- N-rate response
- government-recommended NPK reference
- potential mineral-N reduction
- additional N requirement

"Yield retention" is no longer used.

Relative yield to the government reference is:

100 x treatment yield / N120-P60-K40 reference yield

The lower-N screening threshold is:

relative yield >= 95%


STAGE 5
-------

The Stage 5 site-level N-rate screen selects the lowest TESTED N rate
achieving >=95% relative yield to the maximum observed yield in that
site's tested mineral-N response.

This is a trial-based target-setting screen, not an economic optimum.


FYM
---

FYM + N60 is treated as farmer practice.

AE-N and PFP-N are not calculated for FYM treatments because the
organic-N contribution from FYM is not quantified in the current
harmonised dataset.


MAPS
----

Boundary:

D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

CRS:

EPSG:4326

Axes remain:

Longitude (degrees)
Latitude (degrees)

Each map is clipped to wards within the districts represented in that
study/year/variety block.

No DSM interpolation or extrapolation is applied.


OUTPUTS
-------

D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_study_year_site.csv

D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_study_year_summary.csv

D:\dss\SOIL ADVISORY\outputs\nsaf_stage5_n_rate_target_by_study_year_site.csv

D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_availability_matrix.csv

D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_qc.csv

D:\dss\SOIL ADVISORY\outputs\maps\stage1_6

D:\dss\SOIL ADVISORY\outputs\figures\stage1_6

D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_figure_manifest.csv

D:\dss\SOIL ADVISORY\outputs\run_nsaf_stage1_6.log
