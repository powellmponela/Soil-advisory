from nsaf_stage_common import *
for year in [2017,2018,2019]:
    run_pair_stage(
        f"01d_{year}_p_response", year, "Trial",
        "government_recommendation","p_omission",
        "N120-P60-K40","N120-P0-K40",
        f"{year}: P response under supplied N and K"
    )
