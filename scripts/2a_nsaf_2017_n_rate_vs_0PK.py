from nsaf_compare_common import *

df=load_data()
q=df.loc[
    df["year"].eq(2017)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["P_rate_kg_ha"].eq(60)
    & df["K_rate_kg_ha"].eq(40)
    & df["N_rate_kg_ha"].isin([0,60,120,180,210])
].copy()

q["group"]=q["N_rate_kg_ha"].map({0:"0PK",60:"N60",120:"GR",180:"N180",210:"N210"})
labels={"0PK":"0","N60":"60","GR":"120 (GR)","N180":"180","N210":"210"}
order=["0PK","N60","GR","N180","N210"]

district_violin(
    q,"group",order,labels,COLORS,
    "2017 N-rate response under fixed P60-K40",
    "2a_2017_n_rate_yield.png"
)

targets=["n_rate_60","government_recommendation","n_rate_180","n_rate_210"]
ae=ae_vs_0pk(df.loc[df["year"].eq(2017)],targets)
role_group={
    "n_rate_60":"N60","government_recommendation":"GR",
    "n_rate_180":"N180","n_rate_210":"N210"
}
ae["group"]=ae["treatment_role"].map(role_group)
ae.to_csv(TABLES/"2a_2017_n_rate_AE_vs_0PK.csv",index=False)

district_violin(
    ae,"group",["N60","GR","N180","N210"],labels,COLORS,
    "2017 AE-N by N rate relative to 0PK",
    "2a_2017_n_rate_AE.png",
    value_col="AE_N_vs_0PK_kg_kg",
    ylabel="AE-N (kg grain kg$^{-1}$ N)"
)

ys=site_summary(q,["year","district","site","group"])
map_grid(
    ys,"group",order,labels,"mean_yield_t_ha",
    "2017 site mean yield by N rate",
    "2a_2017_n_rate_yield_maps.png",cmap="YlGnBu"
)
map_grid(
    ae,"group",["N60","GR","N180","N210"],labels,"AE_N_vs_0PK_kg_kg",
    "2017 AE-N by N rate relative to 0PK",
    "2a_2017_n_rate_AE_maps.png",cmap="YlGnBu"
)
