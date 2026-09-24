from nsaf_stage_common import *
for year in [2017,2019]:
    run_pair_stage(
        f"01e_{year}_k_response", year, "Trial",
        "government_recommendation","k_omission",
        "N120-P60-K40","N120-P60-K0",
        f"{year}: K response under supplied N and P"
    )
