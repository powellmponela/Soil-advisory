# ============================================================
# QUEFTS 2019 Maize Demo Analysis - Pooled Baseline
# ============================================================

library(Rquefts)
library(dplyr)

# Load matched 2019 data and pooled controls
input_file <- "Data/nsaf_plots_narc_soil_2019.csv"
control_file <- "Data/nsaf_pooled_controls_2017_2019.csv"
output_file <- "outputs/maize_2019_demo_analysis.csv"

if (!file.exists(input_file) | !file.exists(control_file)) {
  stop("Missing input files for 2019 analysis.")
}

df <- read.csv(input_file)
# Note: Yield_t_ha in the input CSV actually contains kg/ha due to misalignment.
df$Yield_t_ha <- df$Yield_t_ha / 1000 
controls <- read.csv(control_file)

# 1. Pre-process Soil
df$OC <- (df$om_pct / 1.724) * 10
df$P_Olsen <- df$p_olsen_mg_kg / 2.6
df$Exch_K <- (df$k_exch_mg_kg * 0.83 / 2.6) / 39.1

# 2. Calculate Pooled Control Yield by District
control_baseline <- controls %>%
  group_by(District) %>%
  summarise(yield_control_pooled = mean(Yield_t_ha, na.rm=TRUE)) %>%
  ungroup()

df_clean <- df %>%
  filter(!is.na(ph), !is.na(OC), !is.na(P_Olsen), !is.na(Exch_K)) %>%
  left_join(control_baseline, by = "District") %>%
  mutate(yield_control_pooled = ifelse(is.na(yield_control_pooled), mean(controls$Yield_t_ha, na.rm=TRUE), yield_control_pooled))

# 3. Analyze 2019 Plots
results <- df_clean %>%
  rowwise() %>%
  mutate(
    # Native Supply
    n_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[1],
    p_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[2],
    k_supply = nutSupply1(ph, OC, Exch_K, P_Olsen)[3],
    
    # Efficiency based on pooled control
    AE_pooled = (Yield_t_ha - yield_control_pooled) * 1000 / ifelse(N_kg_ha > 0, N_kg_ha, 1),
    NUE = Yield_t_ha * 1000 / ifelse(N_kg_ha > 0, N_kg_ha, 1),
    
    # QUEFTS Optimization (Target 8 t/ha)
    n_rec_quefts = max(0, (200 - n_supply) / 0.5),
    p_rec_quefts = max(0, (40 - p_supply) / 0.2) * 2.29,
    k_rec_quefts = max(0, (200 - k_supply) / 0.5) * 1.21
  ) %>%
  ungroup()

# 4. Summary by District for 2019
summary_stats <- results %>%
  group_by(District) %>%
  summarise(
    n_demos = n(),
    avg_yield_2019 = round(mean(Yield_t_ha, na.rm=TRUE), 2),
    avg_ae_pooled = round(mean(AE_pooled, na.rm=TRUE), 1),
    avg_n_applied = round(mean(N_kg_ha, na.rm=TRUE), 1),
    avg_n_rec_quefts = round(mean(n_rec_quefts, na.rm=TRUE), 1),
    .groups = "drop"
  )

# 5. Export
dir.create("outputs", showWarnings = FALSE)
write.csv(results, "outputs/maize_2019_demo_plot_results.csv", row.names = FALSE)
write.csv(summary_stats, output_file, row.names = FALSE)

cat("\n2019 Demo Analysis completed using pooled 2017-2019 controls.\n")
cat("Results generated for", nrow(results), "demo plots.\n")
cat("Output saved to:", output_file, "\n")
