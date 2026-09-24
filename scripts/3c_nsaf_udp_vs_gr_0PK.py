from nsaf_compare_common import *

df=load_data()
targets=["government_recommendation","udp_reduced_n"]
q=df.loc[
    df["year"].eq(2018)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(["n_omission"]+targets)
].copy()
m={"n_omission":"0PK","government_recommendation":"GR","udp_reduced_n":"UDP"}
labels={"0PK":"0PK","GR":"GR","UDP":"UDP"}
q["group"]=q["treatment_role"].map(m)
order=["0PK","GR","UDP"]

district_violin(q,"group",order,labels,COLORS,"2018 UDP vs GR","3c_2018_udp_yield.png")

ae=ae_vs_0pk(q,targets)
ae["group"]=ae["treatment_role"].map(m)
ae.to_csv(TABLES/"3c_2018_udp_AE_vs_0PK.csv",index=False)
district_violin(
    ae,"group",["GR","UDP"],labels,COLORS,
    "2018 AE-N: UDP and GR relative to 0PK","3c_2018_udp_AE.png",
    value_col="AE_N_vs_0PK_kg_kg",ylabel="AE-N (kg grain kg$^{-1}$ N)"
)

sm=site_summary(q,["year","district","site","group"])
map_grid(sm,"group",order,labels,"mean_yield_t_ha","2018 UDP vs GR — site mean yield","3c_2018_udp_yield_maps.png")
map_grid(ae,"group",["GR","UDP"],labels,"AE_N_vs_0PK_kg_kg","2018 AE-N: UDP and GR relative to 0PK","3c_2018_udp_AE_maps.png")
