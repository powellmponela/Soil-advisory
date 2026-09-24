NSAF STAGE 1-6 V10 - SIDE-BY-SIDE TREATMENTS WITHIN YEAR
=========================================================

Copy the .py files into:

D:\dss\SOIL ADVISORY\scripts

Run:

cd "D:\dss\SOIL ADVISORY"
python .\scripts\run_nsaf_stage1_6.py


FIGURE DESIGN
-------------

For every:

study x year x variety x outcome attribute

the treatments are now shown together in one comparative figure.


MAPS
----

Each outcome has a multi-panel map.

Example:

2019 | T1-T10 core trial | Yield

T1       T2       T5       T6
T7       T8       T9       T10

All treatment panels within the same outcome figure use:

- the same study-district boundary
- the same map extent
- the same colour scale
- the same outcome units

This allows direct treatment comparison within the year.

Up to four treatment panels are shown per row.


DISTRIBUTION FIGURES
--------------------

Each study/year/variety/outcome also receives one treatment-comparison
distribution figure.

Treatments are arranged side by side on the x-axis.

For every treatment:

- the boxplot summarises the site distribution
- individual site observations are overlaid as points
- N rate is included in the treatment label where available


OUTCOME ATTRIBUTES
------------------

Where available:

- Yield (kg/ha)
- Yield response to N (kg/ha)
- Agronomic efficiency of N, AE-N (kg grain/kg N)
- Partial factor productivity of N, PFP-N (kg grain/kg N)
- Relative yield to N120-P-K reference (%)
- Potential mineral-N reduction (kg N/ha)


BOUNDARY
--------

D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

Boundary lines:
light grey

CRS:
EPSG:4326

Map axes:
longitude and latitude in degrees

Maps are clipped to the districts represented in the study/year/variety block.


IMPORTANT
---------

Treatment comparisons remain within study/year/variety blocks.

Individual measured sites are retained.

No DSM interpolation/extrapolation or crop-area scaling is applied.
