from nsaf_stage_common import *
for year in [2017,2018,2019]:
    run_pair_stage(
        f"01b_{year}_pk_without_n", year, "Trial",
        "n_omission","soil_background",
        "N0-P60-K40","N0-P0-K0",
        f"{year}: P+K response without N"
    )
