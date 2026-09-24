# Soil Advisory

Research-oriented decision support for maize nutrient management in Nepal.

This repository translates NSAF maize trial evidence into reproducible agronomic summaries, spatial response analysis, fertilizer-demand scenarios, and advisory-facing web outputs.

## Scientific framing

The analytical sequence is:

`0-0-0 baseline -> nutrient omission -> complete NPK -> N rate -> timing -> FYM / PCU / UDP -> spatial response -> QUEFTS target-yield demand -> potential mineral-N reduction`

Agronomic efficiency of N (AE-N) is retained for treatments with a valid 0PK comparator. Partial factor productivity of mineral N (PFP-N) is used for FYM, PCU and UDP strategies where a consistent 0PK comparator is not available.

The web interface reports trial evidence, spatial response estimates, and model limitations separately. Digital soil maps are treated as modelled spatial covariates, not direct measurements at every pixel.

## Reference

Pandit, N. R., Adhikari, S., Vista, S. P., & Choudhary, D. (2025). Nitrogen Management Utilizing 4R Nutrient Stewardship: A Sustainable Strategy for Enhancing NUE, Reducing Maize Yield Gap and Increasing Farm Profitability. *Nitrogen, 6*(1), 7. https://doi.org/10.3390/nitrogen6010007
