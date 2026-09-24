from nsaf_stage_common import *
for year in [2017,2018,2019]:
    run_pair_stage(
        f"01c_{year}_n_response", year, "Trial",
        "government_recommendation","n_omission",
        "N120-P60-K40","N0-P60-K40",
        f"{year}: N response under supplied P and K"
    )
