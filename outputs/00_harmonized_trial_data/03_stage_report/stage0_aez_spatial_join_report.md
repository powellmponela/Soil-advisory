# Stage 0b AEZ spatial join report

Input maize CSV: `D:\dss\SOIL ADVISORY\outputs\00_harmonized_trial_data\04_inputs_for_next_stage\maize.csv`

AEZ shapefile: `D:\dss\SOIL ADVISORY\Data\ecological zones\Cross_sections_of_Nepal_s_physiographic_regions.shp`

Polygon attribute used for AEZ: `AEZ`

Output maize CSV: `D:\dss\SOIL ADVISORY\outputs\00_harmonized_trial_data\00_data\maize.csv`

Next-stage maize CSV: `D:\dss\SOIL ADVISORY\outputs\00_harmonized_trial_data\04_inputs_for_next_stage\maize.csv`

Rows: 3023

Rows with valid coordinates: 3017

Rows with polygon match: 3017

Rows in target AEZ scope: 1597

Target AEZ classes:

- Terai
- Churia/Siwalik
- Mid-hills

This script converts maize latitude/longitude to points, reprojects points to the polygon CRS, extracts polygon attributes by spatial join, and saves the extracted AEZ attributes back into `maize.csv`.
