from nsaf_compare_common import *

df=load_data()
q=df.loc[
    df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(["soil_background","n_omission","p_omission","k_omission","government_recommendation"])
].copy()

role_to_group={
    "soil_background":"000",
    "n_omission":"0PK",
    "p_omission":"minusP",
    "k_omission":"minusK",
    "government_recommendation":"GR"
}
labels={
    "000":"0–0–0",
    "0PK":"0–60–40 (−N)",
    "minusP":"120–0–40 (−P)",
    "minusK":"120–60–0 (−K)",
    "GR":"120–60–40 (GR)"
}
q["group"]=q["treatment_role"].map(role_to_group)

q.to_csv(TABLES/"1f_omissions_000_gr_observations.csv",index=False)

for year in [2017,2018,2019]:
    y=q.loc[q["year"].eq(year)].copy()
    order=[g for g in ["000","0PK","minusP","minusK","GR"] if (y["group"]==g).any()]
    district_violin(
        y,"group",order,labels,COLORS,
        f"{year}: unfertilized control, nutrient omissions and GR",
        f"1f_omissions_000_gr_{year}.png"
    )

s=site_summary(q,["year","district","site","group"])
for year in [2017,2018,2019]:
    y=s.loc[s["year"].eq(year)].copy()
    order=[g for g in ["000","0PK","minusP","minusK","GR"] if (y["group"]==g).any()]
    map_grid(
        y,"group",order,labels,"mean_yield_t_ha",
        f"{year}: site mean yield — 000, omissions and GR",
        f"1f_omissions_000_gr_{year}_maps.png",
        cmap="YlGnBu"
    )
