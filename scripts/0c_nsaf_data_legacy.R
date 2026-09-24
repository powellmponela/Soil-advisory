# ============================================================
# NSAF maize trial data merge using Carob-like nomenclature
# Summary by year x site x treatment
# ============================================================

options(repos = c(CRAN = "https://cloud.r-project.org"))

pkgs <- c(
  "readxl", "readr", "dplyr", "stringr",
  "purrr", "tibble", "writexl"
)

missing_pkgs <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_pkgs) > 0) install.packages(missing_pkgs, dependencies = TRUE)

invisible(lapply(pkgs, library, character.only = TRUE))

# ============================================================
# Working directory and file paths
# ============================================================

wd <- "C:/Users/PMPONELA/OneDrive - CGIAR/CIMMYT/AURORA/Indo-pacific agrifood productivity"

setwd(wd)

data_dir <- file.path(wd, "Data/NSAF Crops Trial Data/Maize")
out_dir  <- file.path(wd, "outputs")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

f2017 <- file.path(data_dir, "maize_trials_2017.xlsx")
f2018 <- file.path(data_dir, "maize_trials-2018.csv")
f2019 <- file.path(data_dir, "Maize_postharvest_2019 - all versions - labels - 2020-01-23-04-01-40.xlsx")

missing_files <- c(f2017, f2018, f2019)[!file.exists(c(f2017, f2018, f2019))]

if (length(missing_files) > 0) {
  stop(
    "These files were not found:\n",
    paste(missing_files, collapse = "\n")
  )
}

out_merged_csv  <- file.path(out_dir, "merged_maize_trials_carob_like.csv")
out_summary_csv <- file.path(out_dir, "summary_maize_by_year_site_treatment.csv")
out_workbook    <- file.path(out_dir, "maize_trials_merged_carob_summary.xlsx")

# ============================================================
# Helper functions
# ============================================================

safe_sheet <- function(path, preferred = NULL) {
  sh <- readxl::excel_sheets(path)
  if (!is.null(preferred) && preferred %in% sh) {
    preferred
  } else {
    sh[1]
  }
}

get_col <- function(dat, candidates, default = NA_character_) {
  nm <- candidates[candidates %in% names(dat)][1]
  
  if (is.na(nm)) {
    rep(default, nrow(dat))
  } else {
    dat[[nm]]
  }
}

get_col_pos <- function(dat, pos, default = NA_character_) {
  if (!is.na(pos) && pos <= ncol(dat)) {
    dat[[pos]]
  } else {
    rep(default, nrow(dat))
  }
}

chr <- function(x) {
  x <- stringr::str_squish(as.character(x))
  dplyr::na_if(x, "")
}

num <- function(x) {
  suppressWarnings(
    readr::parse_number(
      as.character(x),
      na = c("", "NA", "NaN", "NULL", "null", "N/A")
    )
  )
}

fill_num <- function(x, value) {
  x[is.na(x)] <- value
  x
}

site_id <- function(adm1, adm2) {
  dplyr::case_when(
    !is.na(adm1) & !is.na(adm2) ~ stringr::str_c(adm1, adm2, sep = " | "),
    !is.na(adm1) ~ adm1,
    !is.na(adm2) ~ adm2,
    TRUE ~ NA_character_
  )
}

mean_na <- function(x) {
  if (all(is.na(x))) NA_real_ else mean(x, na.rm = TRUE)
}

sd_na <- function(x) {
  if (sum(!is.na(x)) <= 1) NA_real_ else sd(x, na.rm = TRUE)
}

min_na <- function(x) {
  if (all(is.na(x))) NA_real_ else min(x, na.rm = TRUE)
}

max_na <- function(x) {
  if (all(is.na(x))) NA_real_ else max(x, na.rm = TRUE)
}

# ============================================================
# Standard Carob-like variables
# ============================================================

carob_cols <- c(
  "dataset_id", "source_file", "source_sheet",
  "country", "crop", "year", "season",
  "adm1", "adm2", "site",
  "trial_id", "farmer_id", "farmer_name", "observation_id",
  "trial_type",
  "treatment_code", "treatment", "treatment_group",
  "barcode",
  "N_fertilizer_kg_ha", "P2O5_fertilizer_kg_ha", "K2O_fertilizer_kg_ha",
  "B_fertilizer_kg_ha", "ZnSO4_fertilizer_kg_ha",
  "organic_fertilizer_t_ha",
  "N_source", "N_application_method", "N_application_time",
  "variety", "seed_rate_kg_ha", "planting_window",
  "plant_spacing", "plant_density_ha",
  "latitude", "longitude", "elevation_m", "gps_precision_m",
  "soil_pH", "soil_OM_pct", "soil_N", "soil_P", "soil_K",
  "straw_yield_kg_ha", "cob_yield_kg_ha",
  "grain_yield_raw_kg_ha",
  "thousand_grain_weight_g", "grain_moisture_pct",
  "yield_kg_ha", "yield_t_ha",
  "PFPN_kg_grain_per_kg_N", "AE_N_kg_grain_per_kg_N",
  "notes"
)

# ============================================================
# 2017 dataset
# ============================================================

sheet2017 <- safe_sheet(f2017, preferred = "maize_trials_2017")

raw2017 <- readxl::read_excel(
  f2017,
  sheet = sheet2017,
  .name_repair = "minimal"
)

d2017 <- tibble(
  dataset_id = "nsaf_maize_trials_2017",
  source_file = basename(f2017),
  source_sheet = sheet2017,
  country = "Nepal",
  crop = "maize",
  
  year = fill_num(num(get_col(raw2017, c("Year", "year", "YEAR"), default = 2017)), 2017),
  season = chr(get_col(raw2017, c("Season", "season"))),
  
  adm1 = chr(get_col(raw2017, c("District", "district"))),
  adm2 = chr(get_col(raw2017, c("VDC", "vdc", "Municipality", "municipality"))),
  site = site_id(adm1, adm2),
  
  farmer_id = chr(get_col(raw2017, c("Farmer_id", "farmer_id", "Farmer ID"))),
  farmer_name = chr(get_col(raw2017, c("Farmer's name", "Farmer name", "farmer_name"))),
  observation_id = chr(get_col(raw2017, c("ID", "id", "S.no", "S.No"))),
  trial_id = dplyr::coalesce(
    stringr::str_c(year, farmer_id, sep = "_"),
    observation_id
  ),
  
  trial_type = chr(get_col(raw2017, c("Trial/Demo", "trial_type"))),
  
  treatment_code = chr(get_col(raw2017, c("treatment_code", "Treatment code", "treatment"))),
  treatment = chr(get_col(raw2017, c("treatment", "Treatment", "treatment_label"))),
  treatment_group = chr(get_col(raw2017, c("category", "Category", "treatment_group"))),
  barcode = chr(get_col(raw2017, c("barcode", "Barcode"))),
  
  N_fertilizer_kg_ha = num(get_col(raw2017, c("N_kg_ha", "N_fertilizer_kg_ha"))),
  P2O5_fertilizer_kg_ha = num(get_col(raw2017, c("P2O5_kg_ha", "P2O5_fertilizer_kg_ha"))),
  K2O_fertilizer_kg_ha = num(get_col(raw2017, c("K2O_kg_ha", "K2O_fertilizer_kg_ha"))),
  B_fertilizer_kg_ha = num(get_col(raw2017, c("B_kg_ha", "B_fertilizer_kg_ha"))),
  ZnSO4_fertilizer_kg_ha = num(get_col(raw2017, c("ZnSO4_kg_ha", "ZnSO4_fertilizer_kg_ha"))),
  organic_fertilizer_t_ha = num(get_col(raw2017, c("FYM_t_ha", "organic_fertilizer_t_ha"))),
  
  N_source = chr(get_col(raw2017, c("N_source", "N source"))),
  N_application_method = chr(get_col(raw2017, c("N_methods", "N_method", "N application method"))),
  N_application_time = chr(get_col(raw2017, c("N_time", "N timing", "N_application_time"))),
  
  variety = chr(get_col(raw2017, c("variety", "Variety"))),
  seed_rate_kg_ha = num(get_col(raw2017, c("seed_rate_kg_ha", "Seed rate"))),
  planting_window = chr(get_col(raw2017, c("planting time", "planting_time", "Planting time"))),
  plant_spacing = chr(get_col(raw2017, c("spacing (cm*cm)", "plant_spacing", "Spacing"))),
  plant_density_ha = num(get_col(raw2017, c("plant_population", "plant_density_ha"))),
  
  latitude = num(get_col(raw2017, c("latitude", "Latitude"))),
  longitude = num(get_col(raw2017, c("longitude", "Longitude"))),
  elevation_m = num(get_col(raw2017, c("altitude", "elevation_m", "Elevation"))),
  gps_precision_m = num(get_col(raw2017, c("precision", "gps_precision_m"))),
  
  soil_pH = num(get_col(raw2017, c("pH", "soil_pH"))),
  soil_OM_pct = num(get_col(raw2017, c("OM", "soil_OM_pct"))),
  soil_N = num(get_col(raw2017, c("N", "soil_N"))),
  soil_P = num(get_col(raw2017, c("P", "soil_P"))),
  soil_K = num(get_col(raw2017, c("K", "soil_K"))),
  
  straw_yield_kg_ha = num(get_col(raw2017, c("straw_weight_kg_ha", "Straw_wt_kg_ha"))),
  cob_yield_kg_ha = num(get_col(raw2017, c("cob_wt_kg_ha", "cob_yield_kg_ha"))),
  grain_yield_raw_kg_ha = num(get_col(raw2017, c("grain_yield_kg_ha", "grain_yield_raw_kg_ha"))),
  thousand_grain_weight_g = num(get_col(raw2017, c("1000_grain_wt_gm", "thousand_grain_weight_g"))),
  grain_moisture_pct = num(get_col(raw2017, c("moisture%", "grain_moisture_pct"))),
  
  yield_kg_ha = num(get_col(raw2017, c("Yield_kg_ha", "yield_kg_ha"))),
  yield_t_ha = num(get_col(raw2017, c("Yield_t_ha", "yield_t_ha"))),
  
  PFPN_kg_grain_per_kg_N = num(get_col(raw2017, c("PFPN", "NUE_N", "PFPN_kg_grain_per_kg_N"))),
  AE_N_kg_grain_per_kg_N = num(get_col(raw2017, c("AE_N", "AE_N_kg_grain_per_kg_N"))),
  
  notes = NA_character_
) %>%
  mutate(
    yield_t_ha = if_else(is.na(yield_t_ha) & !is.na(yield_kg_ha), yield_kg_ha / 1000, yield_t_ha),
    treatment = coalesce(treatment, treatment_code)
  )

# ============================================================
# 2018 dataset
# ============================================================

raw2018 <- readr::read_csv(
  f2018,
  show_col_types = FALSE,
  name_repair = "minimal"
)

treat18 <- tibble::tribble(
  ~treatment_code, ~treatment_label,
  "1", "NPK urea split (120-60-40)",
  "2", "NPK PCU basal (120-60-40)",
  "3", "N60 PCU basal (60-60-40)",
  "4", "UDP basal (78-60-40)",
  "5", "N60 urea split (60-60-40)",
  "6", "P omission urea split (120-0-40)",
  "7", "N omission (0-60-40)",
  "8", "Control (0-0-0)",
  "9", "NPK urea split V6/V10 (120-60-40)"
)

d2018 <- tibble(
  dataset_id = "nsaf_maize_trials_2018",
  source_file = basename(f2018),
  source_sheet = "maize_trials-2018",
  country = "Nepal",
  crop = "maize",
  
  year = 2018,
  season = chr(get_col(raw2018, c("Season", "season"))),
  
  adm1 = chr(get_col(raw2018, c("District", "district"))),
  adm2 = chr(get_col(raw2018, c("VDC", "vdc", "Municipality", "municipality"))),
  site = site_id(adm1, adm2),
  
  farmer_id = chr(get_col(raw2018, c("Farmer_id", "farmer_id", "Farmer ID"))),
  farmer_name = chr(get_col(raw2018, c("Farmer's name", "Farmer name", "farmer_name"))),
  observation_id = chr(get_col(raw2018, c("S.no", "S.No", "ID", "id"))),
  trial_id = dplyr::coalesce(
    stringr::str_c(year, adm1, adm2, farmer_name, sep = "_"),
    observation_id
  ),
  
  trial_type = chr(get_col(raw2018, c("Trial/Demo", "trial_type"))),
  
  treatment_code = chr(get_col(raw2018, c("treatment", "Treatment", "treatment_code"))),
  treatment_group = chr(get_col(raw2018, c("category", "Category", "treatment_group"))),
  barcode = chr(get_col(raw2018, c("barcode", "Barcode"))),
  
  N_fertilizer_kg_ha = num(get_col(raw2018, c("N_kg_ha", "N_fertilizer_kg_ha"))),
  P2O5_fertilizer_kg_ha = num(get_col(raw2018, c("P2O5_kg_ha", "P2O5_fertilizer_kg_ha"))),
  K2O_fertilizer_kg_ha = num(get_col(raw2018, c("K2O_kg_ha", "K2O_fertilizer_kg_ha"))),
  B_fertilizer_kg_ha = num(get_col(raw2018, c("B_kg_ha", "B_fertilizer_kg_ha"))),
  ZnSO4_fertilizer_kg_ha = num(get_col(raw2018, c("ZnSO4_kg_ha", "ZnSO4_fertilizer_kg_ha"))),
  organic_fertilizer_t_ha = num(get_col(raw2018, c("FYM_t_ha", "organic_fertilizer_t_ha"))),
  
  N_source = chr(get_col(raw2018, c("N_source", "N source"))),
  N_application_method = chr(get_col(raw2018, c("N_methods", "N_method", "N application method"))),
  N_application_time = chr(get_col(raw2018, c("N_time", "N timing", "N_application_time"))),
  
  variety = chr(get_col(raw2018, c("variety", "Variety"))),
  seed_rate_kg_ha = num(get_col(raw2018, c("seed_rate_kg_ha", "Seed rate"))),
  planting_window = chr(get_col(raw2018, c("planting time", "planting_time", "Planting time"))),
  plant_spacing = chr(get_col(raw2018, c("spacing (cm*cm)", "plant_spacing", "Spacing"))),
  plant_density_ha = num(get_col(raw2018, c("plant_population", "plant_density_ha"))),
  
  latitude = num(get_col(raw2018, c("latitude", "Latitude"))),
  longitude = num(get_col(raw2018, c("longitude", "Longitude"))),
  elevation_m = num(get_col(raw2018, c("altitude", "elevation_m", "Elevation"))),
  gps_precision_m = num(get_col(raw2018, c("precision", "gps_precision_m"))),
  
  soil_pH = num(get_col(raw2018, c("pH", "soil_pH"))),
  soil_OM_pct = num(get_col(raw2018, c("OM", "soil_OM_pct"))),
  soil_N = num(get_col(raw2018, c("N", "soil_N"))),
  soil_P = num(get_col(raw2018, c("P", "soil_P"))),
  soil_K = num(get_col(raw2018, c("K", "soil_K"))),
  
  straw_yield_kg_ha = num(get_col(raw2018, c("Straw_wt_kg_ha", "straw_weight_kg_ha", "straw_yield_kg_ha"))),
  cob_yield_kg_ha = num(get_col(raw2018, c("cob_wt_kg_ha", "cob_yield_kg_ha"))),
  grain_yield_raw_kg_ha = num(get_col(raw2018, c("grain_yield_kg_ha", "grain_yield_raw_kg_ha"))),
  thousand_grain_weight_g = num(get_col(raw2018, c("1000_grain_wt_gm", "thousand_grain_weight_g"))),
  grain_moisture_pct = num(get_col(raw2018, c("moisture%", "grain_moisture_pct"))),
  
  yield_kg_ha = num(get_col(raw2018, c("Yield_kg_ha", "yield_kg_ha"))),
  yield_t_ha = num(get_col(raw2018, c("Yield_t_ha", "yield_t_ha"))),
  
  PFPN_kg_grain_per_kg_N = num(get_col(raw2018, c("NUE_N", "PFPN", "PFPN_kg_grain_per_kg_N"))),
  AE_N_kg_grain_per_kg_N = num(get_col(raw2018, c("AE_N", "AE_N_kg_grain_per_kg_N"))),
  
  notes = NA_character_
) %>%
  left_join(treat18, by = "treatment_code") %>%
  mutate(
    treatment = coalesce(treatment_label, treatment_code),
    yield_t_ha = if_else(is.na(yield_t_ha) & !is.na(yield_kg_ha), yield_kg_ha / 1000, yield_t_ha)
  ) %>%
  select(-treatment_label)

# ============================================================
# 2019 postharvest dataset
# Wide file reshaped into long treatment-block format
# ============================================================

sheet2019 <- safe_sheet(f2019, preferred = "Maize_postharvest_2019")

raw2019 <- readxl::read_excel(
  f2019,
  sheet = sheet2019,
  .name_repair = "minimal"
)

get_site_2019 <- function(dat) {
  district_raw <- chr(get_col(dat, c("District", "district")))
  
  adm1 <- dplyr::recode(
    district_raw,
    "Surket" = "Surkhet",
    .default = district_raw
  )
  
  adm2 <- dplyr::case_when(
    district_raw == "Surket"    ~ chr(get_col(dat, c("Surket", "Surkhet"))),
    district_raw == "Surkhet"   ~ chr(get_col(dat, c("Surket", "Surkhet"))),
    district_raw == "Dang"      ~ chr(get_col(dat, c("Dang"))),
    district_raw == "Palpa"     ~ chr(get_col(dat, c("Palpa"))),
    district_raw == "Kavre"     ~ chr(get_col(dat, c("Kavre"))),
    district_raw == "Doti"      ~ chr(get_col(dat, c("Doti"))),
    district_raw == "Nuwakot"   ~ chr(get_col(dat, c("Nuwakot"))),
    district_raw == "Makwanpur" ~ chr(get_col(dat, c("Makwanpur"))),
    district_raw == "Salyan"    ~ chr(get_col(dat, c("Salyan"))),
    district_raw == "Chitwan"   ~ chr(get_col(dat, c("Chitwan"))),
    TRUE ~ NA_character_
  )
  
  tibble(
    adm1 = adm1,
    adm2 = adm2,
    site = site_id(adm1, adm2)
  )
}

extract_2019_block <- function(dat, treatment_code, start_col) {
  loc <- get_site_2019(dat)
  
  yieldkg <- num(get_col_pos(dat, start_col + 11))
  
  tibble(
    dataset_id = "maize_postharvest_2019",
    source_file = basename(f2019),
    source_sheet = sheet2019,
    country = "Nepal",
    crop = "maize",
    
    year = 2019,
    season = chr(get_col(dat, c("Season", "season"))),
    
    adm1 = loc$adm1,
    adm2 = loc$adm2,
    site = loc$site,
    
    farmer_id = chr(get_col(dat, c("Farmer_id", "farmer_id", "Farmer ID"))),
    farmer_name = chr(get_col(dat, c("Farmer's name", "Farmer name", "farmer_name"))),
    trial_id = chr(get_col(dat, c("_uuid", "uuid", "ID", "id"))),
    observation_id = stringr::str_c(trial_id, treatment_code, sep = "_"),
    
    trial_type = chr(get_col(dat, c("Trial/Demo", "trial_type"))),
    
    treatment_code = treatment_code,
    treatment = treatment_code,
    treatment_group = dplyr::case_when(
      stringr::str_starts(treatment_code, "T") ~ "T block",
      stringr::str_starts(treatment_code, "A") ~ "A block",
      stringr::str_starts(treatment_code, "B") ~ "B block",
      TRUE ~ NA_character_
    ),
    
    barcode = chr(get_col_pos(dat, start_col)),
    
    N_fertilizer_kg_ha = NA_real_,
    P2O5_fertilizer_kg_ha = NA_real_,
    K2O_fertilizer_kg_ha = NA_real_,
    B_fertilizer_kg_ha = NA_real_,
    ZnSO4_fertilizer_kg_ha = NA_real_,
    organic_fertilizer_t_ha = NA_real_,
    
    N_source = NA_character_,
    N_application_method = NA_character_,
    N_application_time = NA_character_,
    
    variety = NA_character_,
    seed_rate_kg_ha = NA_real_,
    planting_window = NA_character_,
    plant_spacing = NA_character_,
    plant_density_ha = NA_real_,
    
    latitude = num(get_col_pos(dat, start_col + 2)),
    longitude = num(get_col_pos(dat, start_col + 3)),
    elevation_m = num(get_col_pos(dat, start_col + 4)),
    gps_precision_m = num(get_col_pos(dat, start_col + 5)),
    
    soil_pH = NA_real_,
    soil_OM_pct = NA_real_,
    soil_N = NA_real_,
    soil_P = NA_real_,
    soil_K = NA_real_,
    
    straw_yield_kg_ha = num(get_col_pos(dat, start_col + 6)),
    cob_yield_kg_ha = num(get_col_pos(dat, start_col + 7)),
    grain_yield_raw_kg_ha = num(get_col_pos(dat, start_col + 8)),
    thousand_grain_weight_g = num(get_col_pos(dat, start_col + 9)),
    grain_moisture_pct = num(get_col_pos(dat, start_col + 10)),
    
    yield_kg_ha = yieldkg,
    yield_t_ha = yieldkg / 1000,
    
    PFPN_kg_grain_per_kg_N = NA_real_,
    AE_N_kg_grain_per_kg_N = NA_real_,
    
    notes = "2019 wide postharvest file reshaped from treatment blocks; fertilizer rates were not embedded in the source file."
  ) %>%
    filter(!is.na(barcode) | !is.na(yield_kg_ha))
}

t_codes <- paste0("T", 1:10)
a_codes <- paste0("A", 1:5)
b_codes <- paste0("B", 1:5)

starts <- c(
  setNames(17 + 12 * (0:9), t_codes),
  setNames(137 + 12 * (0:4), a_codes),
  setNames(197 + 12 * (0:4), b_codes)
)

d2019 <- purrr::map2_dfr(
  names(starts),
  as.integer(starts),
  ~ extract_2019_block(raw2019, treatment_code = .x, start_col = .y)
)

# ============================================================
# Merge standalone Carob-like dataset
# ============================================================

merged_carob <- bind_rows(d2017, d2018, d2019) %>%
  select(all_of(carob_cols)) %>%
  arrange(year, adm1, adm2, farmer_name, treatment_code)

# ============================================================
# Summary by year x site x treatment
# ============================================================

summary_year_site_treatment <- merged_carob %>%
  group_by(
    year, adm1, adm2, site,
    treatment_code, treatment, treatment_group
  ) %>%
  summarise(
    n_obs = n(),
    n_trials = n_distinct(trial_id, na.rm = TRUE),
    n_farmers = n_distinct(farmer_name, na.rm = TRUE),
    n_yield = sum(!is.na(yield_kg_ha)),
    
    mean_yield_kg_ha = mean_na(yield_kg_ha),
    sd_yield_kg_ha = sd_na(yield_kg_ha),
    min_yield_kg_ha = min_na(yield_kg_ha),
    max_yield_kg_ha = max_na(yield_kg_ha),
    
    mean_yield_t_ha = mean_na(yield_t_ha),
    
    mean_N_fertilizer_kg_ha = mean_na(N_fertilizer_kg_ha),
    mean_P2O5_fertilizer_kg_ha = mean_na(P2O5_fertilizer_kg_ha),
    mean_K2O_fertilizer_kg_ha = mean_na(K2O_fertilizer_kg_ha),
    mean_organic_fertilizer_t_ha = mean_na(organic_fertilizer_t_ha),
    
    mean_PFPN_kg_grain_per_kg_N = mean_na(PFPN_kg_grain_per_kg_N),
    mean_AE_N_kg_grain_per_kg_N = mean_na(AE_N_kg_grain_per_kg_N),
    
    mean_straw_yield_kg_ha = mean_na(straw_yield_kg_ha),
    mean_cob_yield_kg_ha = mean_na(cob_yield_kg_ha),
    mean_grain_yield_raw_kg_ha = mean_na(grain_yield_raw_kg_ha),
    mean_grain_moisture_pct = mean_na(grain_moisture_pct),
    
    source_datasets = paste(sort(unique(dataset_id)), collapse = "; "),
    .groups = "drop"
  ) %>%
  arrange(year, adm1, adm2, treatment_code)

# ============================================================
# Treatment lookup
# ============================================================

treatment_lookup <- merged_carob %>%
  group_by(
    year, treatment_code, treatment, treatment_group,
    N_fertilizer_kg_ha, P2O5_fertilizer_kg_ha, K2O_fertilizer_kg_ha,
    organic_fertilizer_t_ha,
    N_source, N_application_method, N_application_time
  ) %>%
  summarise(
    n_obs = n(),
    dataset_id = paste(sort(unique(dataset_id)), collapse = "; "),
    note = if (dplyr::first(year) == 2019) {
      "Treatment code retained from wide source file; fertilizer rates not embedded."
    } else {
      NA_character_
    },
    .groups = "drop"
  ) %>%
  arrange(year, treatment_code)

# ============================================================
# QA counts
# ============================================================

qa_counts <- merged_carob %>%
  count(year, dataset_id, source_file, name = "n_rows") %>%
  arrange(year, dataset_id)

qa_missing <- merged_carob %>%
  summarise(
    total_rows = n(),
    missing_year = sum(is.na(year)),
    missing_site = sum(is.na(site)),
    missing_treatment = sum(is.na(treatment_code)),
    missing_yield = sum(is.na(yield_kg_ha)),
    missing_N_rate = sum(is.na(N_fertilizer_kg_ha))
  )

# ============================================================
# Data dictionary
# ============================================================

data_dictionary <- tibble(variable = carob_cols) %>%
  mutate(
    description = case_when(
      variable == "dataset_id" ~ "Harmonized dataset identifier.",
      variable == "source_file" ~ "Original source file name.",
      variable == "source_sheet" ~ "Original sheet or data source.",
      variable == "country" ~ "Country.",
      variable == "crop" ~ "Crop.",
      variable == "year" ~ "Trial or observation year.",
      variable == "season" ~ "Cropping season where available.",
      variable == "adm1" ~ "District or first administrative level.",
      variable == "adm2" ~ "VDC, municipality, or second administrative level.",
      variable == "site" ~ "Combined site identifier.",
      variable == "trial_id" ~ "Trial-level or farmer-level identifier.",
      variable == "farmer_id" ~ "Farmer identifier where available.",
      variable == "farmer_name" ~ "Farmer name.",
      variable == "observation_id" ~ "Unique observation identifier.",
      variable == "trial_type" ~ "Trial or demonstration classification.",
      variable == "treatment_code" ~ "Treatment code from source data.",
      variable == "treatment" ~ "Treatment label.",
      variable == "treatment_group" ~ "Treatment category or block.",
      variable == "barcode" ~ "Plot or sample barcode.",
      variable == "N_fertilizer_kg_ha" ~ "Nitrogen fertilizer rate, kg N ha-1.",
      variable == "P2O5_fertilizer_kg_ha" ~ "Phosphorus fertilizer rate, kg P2O5 ha-1.",
      variable == "K2O_fertilizer_kg_ha" ~ "Potassium fertilizer rate, kg K2O ha-1.",
      variable == "B_fertilizer_kg_ha" ~ "Boron fertilizer rate, kg ha-1.",
      variable == "ZnSO4_fertilizer_kg_ha" ~ "Zinc sulphate fertilizer rate, kg ha-1.",
      variable == "organic_fertilizer_t_ha" ~ "Organic fertilizer or FYM rate, t ha-1.",
      variable == "N_source" ~ "Nitrogen fertilizer source.",
      variable == "N_application_method" ~ "Nitrogen application method.",
      variable == "N_application_time" ~ "Nitrogen application timing.",
      variable == "variety" ~ "Maize variety or hybrid.",
      variable == "seed_rate_kg_ha" ~ "Seed rate, kg ha-1.",
      variable == "planting_window" ~ "Planting time or window.",
      variable == "plant_spacing" ~ "Plant spacing.",
      variable == "plant_density_ha" ~ "Plant population or density, plants ha-1.",
      variable == "latitude" ~ "Latitude.",
      variable == "longitude" ~ "Longitude.",
      variable == "elevation_m" ~ "Elevation, m.",
      variable == "gps_precision_m" ~ "GPS precision, m.",
      variable == "soil_pH" ~ "Soil pH.",
      variable == "soil_OM_pct" ~ "Soil organic matter, percent.",
      variable == "soil_N" ~ "Soil nitrogen value from source data.",
      variable == "soil_P" ~ "Soil phosphorus value from source data.",
      variable == "soil_K" ~ "Soil potassium value from source data.",
      variable == "straw_yield_kg_ha" ~ "Straw yield, kg ha-1.",
      variable == "cob_yield_kg_ha" ~ "Cob yield, kg ha-1.",
      variable == "grain_yield_raw_kg_ha" ~ "Raw grain yield, kg ha-1.",
      variable == "thousand_grain_weight_g" ~ "Thousand grain weight, g.",
      variable == "grain_moisture_pct" ~ "Grain moisture, percent.",
      variable == "yield_kg_ha" ~ "Reported or moisture-corrected grain yield, kg ha-1.",
      variable == "yield_t_ha" ~ "Reported or moisture-corrected grain yield, t ha-1.",
      variable == "PFPN_kg_grain_per_kg_N" ~ "Partial factor productivity of nitrogen, kg grain per kg N.",
      variable == "AE_N_kg_grain_per_kg_N" ~ "Agronomic efficiency of nitrogen, kg grain increase per kg N.",
      variable == "notes" ~ "Processing notes.",
      TRUE ~ "Carob-like harmonized variable."
    )
  )

# ============================================================
# Export outputs
# ============================================================

readr::write_csv(merged_carob, out_merged_csv)
readr::write_csv(summary_year_site_treatment, out_summary_csv)

writexl::write_xlsx(
  list(
    merged_carob = merged_carob,
    summary_year_site_treatment = summary_year_site_treatment,
    treatment_lookup = treatment_lookup,
    qa_counts = qa_counts,
    qa_missing = qa_missing,
    data_dictionary = data_dictionary
  ),
  path = out_workbook
)

# ============================================================
# Print completion summary
# ============================================================

cat("\nMerge completed.\n")
cat("Rows in merged dataset:", nrow(merged_carob), "\n")
cat("Rows in summary table:", nrow(summary_year_site_treatment), "\n\n")

cat("Output files:\n")
cat(out_merged_csv, "\n")
cat(out_summary_csv, "\n")
cat(out_workbook, "\n\n")

print(qa_counts)
print(qa_missing)