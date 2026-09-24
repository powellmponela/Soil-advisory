NSAF comparative plotting package

Design restored to the agreed district-comparative style:
- violin + observed points;
- Overall followed by districts on the x-axis;
- treatment/comparator groups shown side by side within each district;
- graphs and maps saved as separate figures;
- exact estimates saved under outputs\tables;
- maps retain common comparable extent and common color scales within each figure;
- no numeric point labels on maps.

Comparative groups:
1f  000 vs nutrient omissions vs GR
2a  2017 N rates 0,60,120,180,210 under P60-K40; AE-N relative to 0PK
3a  N timing vs GR; AE-N for each N treatment relative to 0PK
3b  PCU vs GR; AE-N relative to 0PK
3c  UDP vs GR; AE-N relative to 0PK
3d  FYM + reduced mineral N vs GR; AE-N of inorganic N relative to 0PK using the recorded inorganic-N rate
4a  Demo Hybrid vs OPV across districts: 2018 descriptive comparison and 2019 matched management strategies

Important:
- AE-N is calculated using inorganic N only: (Y_treatment - Y_0PK) * 1000 / N_inorganic. The inorganic-N rate is read from N_rate_kg_ha in the harmonised dataframe.
- 0PK means N0-P60-K40 (N omission), not 0-0-0.
- 2018 Demo Hybrid-vs-OPV is descriptive because the 2018 source design is not the same paired strategy structure as 2019.
- Farmers' seed in the 2018 Demo remains in the saved full observation table but is excluded from the requested Hybrid-vs-OPV figure.
