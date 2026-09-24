NSAF STAGE 1-6 V5: TRUE-SIZE PROJECTED MAP CRS
==============================================

Project root:
D:\dss\SOIL ADVISORY

Boundary:
D:\dss\SOIL ADVISORY\Data\boundary\ward_level_boundary.gpkg

Mapping CRS:
ESRI:102306 - Nepal Nagarkot TM

The boundary is reprojected from its stored CRS into Nepal Nagarkot TM.
Trial-site longitude/latitude coordinates are treated as WGS84 (EPSG:4326)
and transformed into the same projected CRS before plotting.

Map coordinates are therefore in metres internally and displayed as kilometres.
The plotting aspect ratio is 1:1 in projected coordinate space.

This avoids plotting Nepal in longitude/latitude degrees, where east-west and
north-south scales are not directly comparable.

Run:
cd "D:\dss\SOIL ADVISORY"
python .\scripts\run_nsaf_stage1_6.py

Outputs:
D:\dss\SOIL ADVISORY\outputs\maps\stage1_6
D:\dss\SOIL ADVISORY\outputs\figures\stage1_6

These remain measured trial-site maps. No DSM extrapolation or crop-area scaling
is applied at this stage.
