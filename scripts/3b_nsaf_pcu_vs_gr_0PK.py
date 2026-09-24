from nsaf_compare_common import *

df=load_data()
year=2018
targets=["government_recommendation","pcu_full_n","pcu_half_n"]
q=df.loc[
    df["year"].eq(year)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(["n_omission"]+targets)
].copy()
m={"n_omission":"0PK","government_recommendation":"GR","pcu_full_n":"PCU120","pcu_half_n":"PCU60"}
labels={"0PK":"0PK","GR":"GR N120","PCU120":"PCU N120","PCU60":"PCU N60"}
q["group"]=q["treatment_role"].map(m)
order=["0PK","GR","PCU120","PCU60"]

district_violin(q,"group",order,labels,COLORS,"2018 PCU vs GR","3b_2018_pcu_yield.png")

ae=ae_vs_0pk(q,targets)
ae["group"]=ae["treatment_role"].map(m)
ae.to_csv(TABLES/"3b_2018_pcu_AE_vs_0PK.csv",index=False)
district_violin(
    ae,"group",["GR","PCU120","PCU60"],labels,COLORS,
    "2018 AE-N: PCU and GR relative to 0PK","3b_2018_pcu_AE.png",
    value_col="AE_N_vs_0PK_kg_kg",ylabel="AE-N (kg grain kg$^{-1}$ N)"
)

sm=site_summary(q,["year","district","site","group"])
map_grid(sm,"group",order,labels,"mean_yield_t_ha","2018 PCU vs GR — site mean yield","3b_2018_pcu_yield_maps.png")
map_grid(ae,"group",["GR","PCU120","PCU60"],labels,"AE_N_vs_0PK_kg_kg","2018 AE-N: PCU and GR relative to 0PK","3b_2018_pcu_AE_maps.png")
