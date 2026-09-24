NSAF STAGE 1-6 V4: FIXED WARD BOUNDARY
======================================

Copy the .py files into:

D:\dss\SOIL ADVISORY\scripts

Run from project root:

cd "D:\dss\SOIL ADVISORY"
python .\scripts\run_nsaf_stage1_6.py


FIXED MAP BOUNDARY
------------------

All maps now use:

D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

The mapping script no longer searches for alternative boundary files.

The GeoPackage is loaded with geopandas and transformed to EPSG:4326 so that
trial-site latitude/longitude points and ward polygons use the same CRS.


SEQUENCE
--------

0c_nsaf_data_legacy.py
1a_nsaf_stage1_6_descriptives.py
1b_nsaf_stage1_6_maps_figures.py


OUTPUTS
-------

D:\dss\SOIL ADVISORY\outputs\maps\stage1_6
D:\dss\SOIL ADVISORY\outputs\figures\stage1_6
D:\dss\SOIL ADVISORY\outputs\nsaf_stage1_6_figure_manifest.csv


IMPORTANT
---------

The ward layer is used only as the cartographic boundary for the measured trial-site maps.
No ward-level interpolation or DSM extrapolation is performed at this stage.
