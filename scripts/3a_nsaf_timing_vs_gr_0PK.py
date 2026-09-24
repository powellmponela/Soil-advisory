from nsaf_compare_common import *

df=load_data()

for year,targets,label_map in [
    (2018,["government_recommendation","n_timing_v6_v10"],
     {"government_recommendation":"GR","n_timing_v6_v10":"Timing"}),
    (2019,["government_recommendation","n_timing_v8","n_timing_v6_v10"],
     {"government_recommendation":"GR","n_timing_v8":"Timing V8","n_timing_v6_v10":"Timing V6/V10"})
]:
    q=df.loc[
        df["year"].eq(year)
        & df["dataset_type"].astype(str).str.lower().eq("trial")
        & df["treatment_role"].isin(["n_omission"]+targets)
    ].copy()
    q["group"]=q["treatment_role"].map({"n_omission":"0PK",**label_map})
    labels={g:g for g in q["group"].dropna().unique()}
    order=[g for g in ["0PK","GR","Timing","Timing V8","Timing V6/V10"] if (q["group"]==g).any()]
    colors={**COLORS,"Timing V8":"#9467BD","Timing V6/V10":"#6A51A3"}

    district_violin(
        q,"group",order,labels,colors,
        f"{year}: N timing vs GR",
        f"3a_{year}_timing_yield.png"
    )

    ae=ae_vs_0pk(q,targets)
    ae["group"]=ae["treatment_role"].map(label_map)
    ae.to_csv(TABLES/f"3a_{year}_timing_AE_vs_0PK.csv",index=False)
    ae_order=[g for g in order if g!="0PK"]

    district_violin(
        ae,"group",ae_order,labels,colors,
        f"{year}: AE-N for timing treatments vs 0PK",
        f"3a_{year}_timing_AE.png",
        value_col="AE_N_vs_0PK_kg_kg",
        ylabel="AE-N (kg grain kg$^{-1}$ N)"
    )

    sm=site_summary(q,["year","district","site","group"])
    map_grid(sm,"group",order,labels,"mean_yield_t_ha",
             f"{year}: N timing and GR — site mean yield",
             f"3a_{year}_timing_yield_maps.png",cmap="YlGnBu")
    map_grid(ae,"group",ae_order,labels,"AE_N_vs_0PK_kg_kg",
             f"{year}: AE-N for timing treatments vs 0PK",
             f"3a_{year}_timing_AE_maps.png",cmap="YlGnBu")
