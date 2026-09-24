NSAF MAIZE FINAL 0a-1g RESEARCH WORKFLOW

FIXED STAGES
0a  Ingest and harmonise
1a  Unfertilized control (0-0-0)
1b  Unfertilized control vs N omission (-N): yield response to P+K
1c  Unfertilized control vs P omission (-P): yield response to N+K
1d  Unfertilized control vs K omission (-K): yield response to N+P
1e  Yield under N, P and K omission: year x nutrient
1f  Unfertilized control + omissions + government recommendation
1g  Government recommendation vs omissions: yield response to N/P/K and AE-N/AE-P/AE-K

AGRONOMIC DEFINITIONS
Yield response to N = Y_GR - Y_-N
Yield response to P = Y_GR - Y_-P
Yield response to K = Y_GR - Y_-K
AE-N = (Y_GR - Y_-N) / 120 kg N ha-1
AE-P = (Y_GR - Y_-P) / 60 kg P ha-1
AE-K = (Y_GR - Y_-K) / 40 kg K ha-1

2018 has no K-omission treatment in the harmonised Trial design; K response and AE-K remain unavailable.

DATA SOURCE
All Stage 1 scripts read only:
D:\dss\SOIL ADVISORY\Data\NSAF Crops Trial Data\Maize\harmonised\nsaf_maize_key_variables.csv

YIELD
2017: reported analytical yield used as-is.
2018 and 2019: recorded grain yield + measured moisture -> dry yield -> yield at 14% MC.
Dry yield = recorded yield * (100 - MC) / 100
Yield at 14% MC = dry yield / 0.86

FIGURE STYLE
- violin + individual scatter points
- measured observations plotted above summary layers
- related graphs and maps on the same figure
- district names shown as callouts
- maps limited to represented study districts
- yield maps use light-to-dark sequential color
- response maps: negative red, zero yellow, positive green
- AE-N: YlGnBu; AE-P: YlOrBr; AE-K: PuRd, light-to-dark
- no subfolders under outputs\figures or outputs\maps

MAP LABEL RULE
- District names are retained as callouts.
- Numeric site values are not printed on maps; estimates remain in outputs\tables and are represented by point colour/colorbar.
