# ============================================================
# QUEFTS Western Nepal - high-resolution primary surface
# ============================================================

if (!requireNamespace("Rquefts", quietly = TRUE)) {
  install.packages("Rquefts", repos = "https://cloud.r-project.org")
}

library(Rquefts)
library(dplyr)

input_file <- "Data/dsm_western_terai_midhill_pixel-centroid.csv"
output_file <- "outputs/maize_quefts_western_highres_pixels.csv"
target_yields_t_ha <- c(6, 8, 10)

if (!file.exists(input_file)) {
  stop("High-resolution input not found. Run 1c_extract_narc_western_highres_primary.py first.")
}

baseline <- read.csv(input_file)
required <- c("province", "district", "lat", "lon", "ph", "om_pct",
              "p_olsen_mg_kg", "k_exch_mg_kg")
missing <- setdiff(required, names(baseline))
if (length(missing) > 0) stop(paste("Missing columns:", paste(missing, collapse=", ")))

baseline$OC <- (baseline$om_pct / 1.724) * 10
baseline$P_Olsen <- baseline$p_olsen_mg_kg / 2.6
baseline$Exch_K <- (baseline$k_exch_mg_kg * 0.83 / 2.6) / 39.1

clean <- baseline %>%
  filter(!is.na(ph), !is.na(OC), !is.na(P_Olsen), !is.na(Exch_K))
if (nrow(clean) == 0) stop("No complete DSM soil records available for QUEFTS.")

native <- clean %>%
  rowwise() %>%
  mutate(
    n_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[1],
    p_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[2],
    k_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[3]
  ) %>%
  ungroup()

IE_N <- 40
IE_P <- 200
IE_K <- 40
RE_N <- 0.50
RE_P <- 0.20
RE_K <- 0.50

results <- bind_rows(lapply(target_yields_t_ha, function(target_t_ha) {
  target_kg_ha <- target_t_ha * 1000
  n_uptake_req <- target_kg_ha / IE_N
  p_uptake_req <- target_kg_ha / IE_P
  k_uptake_req <- target_kg_ha / IE_K

  native %>%
    mutate(
      target_yield_t_ha = target_t_ha,
      quefts_N_kg_ha = pmax(0, (n_uptake_req - n_supply) / RE_N),
      quefts_P2O5_kg_ha = pmax(0, (p_uptake_req - p_supply) / RE_P) * 2.29,
      quefts_K2O_kg_ha = pmax(0, (k_uptake_req - k_supply) / RE_K) * 1.21,
      IE_N_kg_grain_per_kg_uptake = IE_N,
      RE_N_fraction = RE_N,
      dsm_interpretation = "modelled spatial covariate"
    )
}))

dir.create("outputs", showWarnings = FALSE)
write.csv(results, output_file, row.names = FALSE)
cat("High-resolution QUEFTS completed for", nrow(results), "pixel-scenarios.\n")
cat("Output:", output_file, "\n")
