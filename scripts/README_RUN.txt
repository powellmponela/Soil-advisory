NSAF SOIL ADVISORY - RERUN FILES
================================

Project root:
D:\dss\SOIL ADVISORY

Existing source data:
D:\dss\SOIL ADVISORY\Data\NSAF Crops Trial Data\Maize

Existing scripts:
D:\dss\SOIL ADVISORY\scripts

Existing outputs:
D:\dss\SOIL ADVISORY\outputs

FILES
-----
1a_nsaf_stage1_6_descriptives.py
    Reads the legacy 859-row summary produced by 0c_nsaf_data_legacy.py.
    Keeps study/year/variety/site separate and produces Stage 1-6 tables.

run_nsaf_stage1_6.py
    Runs sequentially:
      1. 0c_nsaf_data_legacy.py
      2. 1a_nsaf_stage1_6_descriptives.py

The existing 0c_nsaf_data_legacy.py is not replaced.

INSTALL
-------
Copy both .py files into:
D:\dss\SOIL ADVISORY\scripts

RUN
---
Open terminal at:
D:\dss\SOIL ADVISORY

Run:
python .\scripts\run_nsaf_stage1_6.py

Or run separately:
python .\scripts\0c_nsaf_data_legacy.py
python .\scripts\1a_nsaf_stage1_6_descriptives.py

OUTPUTS
-------
D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_study_year_site.csv
D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_study_year_summary.csv
D:\dss\SOIL ADVISORY\outputs\nsaf_stage5_target_by_study_year_site.csv
D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_availability_matrix.csv
D:\dss\SOIL ADVISORY\outputs\run_nsaf_stage1_6.log

2019 raw-file variety mapping used by the project:
A = Hybrid
B = OPV

Current target/saving outputs remain kg N/ha. No DSM extrapolation and no
district crop-area scaling are applied at this step.
