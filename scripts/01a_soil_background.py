from nsaf_stage_common import *
df=load_data()
q=df[(df["dataset_type"].astype(str).str.lower()=="trial") & (df["treatment_role"]=="soil_background")].copy()
plot_violin_scatter(q,["soil_background"],{"soil_background":"N0-P0-K0"},FIGURES/"01a_soil_background_yield_violin_scatter.png","Soil background")
for year in [2017,2018,2019]:
    qq=q[q["year"]==year]
    plot_yield_map(qq,"soil_background",f"{year}: N0-P0-K0",MAPS/f"01a_soil_background_{year}_map.png")
