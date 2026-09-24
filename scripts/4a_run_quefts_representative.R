# ============================================================
# QUEFTS Fertilizer Recommendation Model for Maize (Eastern Nepal)
# ============================================================

# Ensure Rquefts is installed
if (!requireNamespace("Rquefts", quietly = TRUE)) {
  install.packages("Rquefts", repos = "https://cloud.r-project.org")
}
library(Rquefts)

# Load data
input_file <- "Data/narc_baseline_maize.csv"
output_file <- "outputs/maize_quefts_recommendations.csv"

if (!file.exists(input_file)) {
  stop("Input file not found. Run Python extraction script first.")
}

baseline <- read.csv(input_file)

# Convert NARC units to QUEFTS inputs
# OC (g/kg) = (OM % / 1.724) * 10
# P-Olsen (mg/kg) = P (kg/ha) / 2.6
# Exch K (mmol/kg) = (K (kg/ha) * 0.83 / 2.6) / 39.1

baseline$OC <- (baseline$om_pct / 1.724) * 10
baseline$P_Olsen <- baseline$p_olsen_mg_kg / 2.6
baseline$Exch_K <- (baseline$k_exch_mg_kg * 0.83 / 2.6) / 39.1

# Remove rows with missing critical soil data
clean_data <- baseline[!is.na(baseline$ph) & !is.na(baseline$OC) & !is.na(baseline$P_Olsen) & !is.na(baseline$Exch_K), ]

if (nrow(clean_data) == 0) {
  stop("No valid soil data for QUEFTS model.")
}

# Define QUEFTS yield target
y_target <- 8000 # 8 t/ha target yield

# Run QUEFTS for each location
recommendations <- data.frame()

for (i in 1:nrow(clean_data)) {
  site <- clean_data[i, ]
  
  # Estimate native nutrient supply using nutSupply1
  # Arguments: pH, SOC, Kex, Polsen
  supply <- nutSupply1(
    pH = site$ph,
    SOC = site$OC,
    Kex = site$Exch_K,
    Polsen = site$P_Olsen
  )
  
  # Nutrient requirements for 8 t/ha yield
  # Internal efficiencies for Maize (kg grain / kg nutrient uptake):
  # N=40, P=200, K=40 (Standard values)
  n_uptake_req <- y_target / 40  # 200 kg N
  p_uptake_req <- y_target / 200 # 40 kg P
  k_uptake_req <- y_target / 40  # 200 kg K
  
  # Fertilizer Gap Calculation
  # Fertilizer req = (Uptake_Req - Native_Supply) / Recovery_Efficiency
  # Typical RE: N=0.5, P=0.2, K=0.5
  n_fert_req <- max(0, (n_uptake_req - supply[1]) / 0.5)
  p_fert_req <- max(0, (p_uptake_req - supply[2]) / 0.2)
  k_fert_req <- max(0, (k_uptake_req - supply[3]) / 0.5)
  
  rec <- data.frame(
    district = site$district_requested,
    lat = site$lat,
    lon = site$lon,
    ph = site$ph,
    om_pct = site$om_pct,
    native_N_supply_kg_ha = supply[1],
    native_P_supply_kg_ha = supply[2],
    native_K_supply_kg_ha = supply[3],
    rec_N_kg_ha = n_fert_req,
    rec_P2O5_kg_ha = p_fert_req * 2.29,
    rec_K2O_kg_ha = k_fert_req * 1.21,
    narc_urea_total_kg_ha = site$maize_urea_total,
    narc_dap_kg_ha = site$maize_dap,
    narc_mop_kg_ha = site$maize_mop
  )
  
  recommendations <- rbind(recommendations, rec)
}

# Export results
dir.create("outputs", showWarnings = FALSE)
write.csv(recommendations, output_file, row.names = FALSE)

cat("\nQUEFTS nutrient supply modeling completed.\n")
cat("Recommendations generated for", nrow(recommendations), "locations in Eastern Nepal.\n")
cat("Output saved to:", output_file, "\n")
