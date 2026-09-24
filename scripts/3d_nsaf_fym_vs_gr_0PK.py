from nsaf_compare_common import *

df=load_data()
targets=["government_recommendation","fym_half_n"]
q=df.loc[
    df["year"].eq(2018)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(["n_omission"]+targets)
].copy()
m={"n_omission":"0PK","government_recommendation":"GR","fym_half_n":"FYM60"}
labels={"0PK":"0PK","GR":"GR N120","FYM60":"FYM + N60"}
q["group"]=q["treatment_role"].map(m)
order=["0PK","GR","FYM60"]

district_violin(q,"group",order,labels,COLORS,"2018 FYM + reduced mineral N vs GR","3d_2018_fym_yield.png")

ae=ae_vs_0pk(q,targets)
ae["group"]=ae["treatment_role"].map(m)
ae.to_csv(TABLES/"3d_2018_fym_AE_vs_0PK.csv",index=False)
district_violin(
    ae,"group",["GR","FYM60"],labels,COLORS,
    "2018 AE-N of inorganic N: FYM + N60 and GR relative to 0PK",
    "3d_2018_fym_AE.png",
    value_col="AE_N_vs_0PK_kg_kg",
    ylabel="AE-N of inorganic N (kg grain kg$^{-1}$ N)"
)

sm=site_summary(q,["year","district","site","group"])
map_grid(sm,"group",order,labels,"mean_yield_t_ha","2018 FYM + reduced N vs GR — site mean yield","3d_2018_fym_yield_maps.png")
map_grid(ae,"group",["GR","FYM60"],labels,"AE_N_vs_0PK_kg_kg","2018 AE-N of inorganic N relative to 0PK","3d_2018_fym_AE_maps.png")
