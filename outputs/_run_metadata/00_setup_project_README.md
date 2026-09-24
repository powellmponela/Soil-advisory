# Soil Advisory project setup

Project root: `D:\dss\SOIL ADVISORY`

This setup script creates the stage-wise folder structure and manifests. It does not delete input data and does not call external APIs.

Run order starts with:

```text
00_setup_project.py
0a_prepare_input_inventory.py
0b...
```

Soil data policy:
1. Use publication-reported soil values first.
2. Fill missing values from locally downloaded DSM layers in `Data/dsm`.
3. Preserve native DSM resolution.
4. Do not call the NARC DSM API.
5. Use ISRIC only for supplemental soil variables not available from local DSM.
