# ============================================================
# QUEFTS CIMMYT Trial Analysis - Strategy Comparison
# ============================================================

library(Rquefts)
library(dplyr)

# Load matched trial and soil data
input_file <- "Data/nsaf_plots_narc_soil.csv"
output_file <- "outputs/maize_cimmyt_strategy_comparison.csv"

if (!file.exists(input_file)) {
  stop("Matched trial/soil file not found.")
}

df <- read.csv(input_file)

# 1. Pre-process Soil Data for QUEFTS
df$OC <- (df$om_pct / 1.724) * 10
df$P_Olsen <- df$p_olsen_mg_kg / 2.6
df$Exch_K <- (df$k_exch_mg_kg * 0.83 / 2.6) / 39.1

# Clean missing values
df_clean <- df %>%
  filter(!is.na(ph), !is.na(OC), !is.na(P_Olsen), !is.na(Exch_K))

# 2. Identify Control Yields (Treatments with 0 N)
control_yields <- df_clean %>%
  filter(N_kg_ha == 0) %>%
  group_by(District) %>%
  summarise(yield_control = mean(Yield_t_ha, na.rm=TRUE)) %>%
  ungroup()

df_clean <- df_clean %>%
  left_join(control_yields, by = "District") %>%
  mutate(yield_control = ifelse(is.na(yield_control), 2.0, yield_control))

# 3. Compare Strategies per Plot
results <- df_clean %>%
  rowwise() %>%
  mutate(
    # Native Supply
    n_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[1],
    p_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[2],
    k_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[3],
    
    # Strategy A: Trial Actuals
    uptake_N_trial = n_supply + (N_kg_ha * 0.5),
    uptake_P_trial = p_supply + (P2O5_kg_ha / 2.29 * 0.2),
    uptake_K_trial = k_supply + (K2O_kg_ha / 1.21 * 0.5),
    
    # QUEFTS predicted yield (IE: N=40, P=200, K=40)
    yield_trial_pred = min(uptake_N_trial * 40, uptake_P_trial * 200, uptake_K_trial * 40) / 1000,
    
    # Strategy B: QUEFTS Optimized (Target 8 t/ha)
    n_rec_quefts = max(0, (200 - n_supply) / 0.5),
    p_rec_quefts = max(0, (40 - p_supply) / 0.2) * 2.29,
    k_rec_quefts = max(0, (200 - k_supply) / 0.5) * 1.21,
    
    # Efficiency Calculations
    AE_trial = (Yield_t_ha - yield_control) * 1000 / ifelse(N_kg_ha > 0, N_kg_ha, 1),
    NUE_trial = Yield_t_ha * 1000 / ifelse(N_kg_ha > 0, N_kg_ha, 1)
  ) %>%
  ungroup()

# 4. Summary statistics
summary_stats <- results %>%
  group_by(District) %>%
  summarise(
    n_plots = n(),
    avg_yield_trial = round(mean(Yield_t_ha, na.rm=TRUE), 2),
    avg_ae_trial = round(mean(AE_trial, na.rm=TRUE), 1),
    avg_n_applied_trial = round(mean(N_kg_ha, na.rm=TRUE), 1),
    avg_n_rec_quefts = round(mean(n_rec_quefts, na.rm=TRUE), 1),
    avg_p_rec_quefts = round(mean(p_rec_quefts, na.rm=TRUE), 1),
    .groups = "drop"
  )

# 5. Export
dir.create("outputs", showWarnings = FALSE)
write.csv(results, "outputs/maize_cimmyt_plot_results.csv", row.names = FALSE)
write.csv(summary_stats, output_file, row.names = FALSE)

cat("\nCIMMYT Trial Analysis completed.\n")
cat("Comparison generated for", nrow(results), "plots across", nrow(summary_stats), "districts.\n")
cat("Output saved to:", output_file, "\n")
