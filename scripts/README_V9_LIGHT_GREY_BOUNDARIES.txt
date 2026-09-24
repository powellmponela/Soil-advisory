NSAF STAGE 1-6 V9 - LIGHT GREY BOUNDARIES
=========================================

Copy the .py files into:

D:\dss\SOIL ADVISORY\scripts

Then run from the project root:

cd "D:\dss\SOIL ADVISORY"
python .\scripts\run_nsaf_stage1_6.py

Mapping settings
----------------

Boundary:
D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

CRS:
EPSG:4326

Map clipping:
Only wards in the districts represented in each study/year/variety block.

Boundary styling:
All ward boundary lines are light grey so the measured trial-site
agronomic values remain the visually dominant layer.

Agronomic point colour scales are unchanged.

No DSM interpolation/extrapolation or crop-area scaling is applied.
