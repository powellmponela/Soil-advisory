from nsaf_stage1_common import *

df=trial_only(load_data())
boundary=load_boundary()

specs=[
    ("N","n_omission",120.0),
    ("P","p_omission",60.0),
    ("K","k_omission",40.0),
]

response_rows=[]
for nutrient,omission,rate in specs:
    q=df.loc[df["treatment_role"].isin(["government_recommendation",omission])].copy()
    resp=paired_site_response(q,"government_recommendation",omission)
    if resp.empty:
        continue
    resp["nutrient"]=nutrient
    resp["yield_response_t_ha"]=resp["response_t_ha"]
    resp[f"AE_{nutrient}_kg_kg"]=resp["yield_response_t_ha"]*1000.0/rate
    response_rows.append(resp)

response=pd.concat(response_rows,ignore_index=True) if response_rows else pd.DataFrame()
response.to_csv(TABLES/"1g_nutrient_yield_response_by_site.csv",index=False)
fixed_districts=set(response["district"].dropna()) if not response.empty else set()

keys=["year","study","dataset_type","district","site","latitude","longitude"]
ae_wide=None
for nutrient,_,_ in specs:
    col=f"AE_{nutrient}_kg_kg"
    if response.empty or col not in response.columns:
        continue
    sub=response.loc[response["nutrient"].eq(nutrient),keys+[col]].copy()
    if sub.empty:
        continue
    ae_wide=sub if ae_wide is None else ae_wide.merge(sub,on=keys,how="outer")
if ae_wide is None:
    ae_wide=pd.DataFrame(columns=keys+["AE_N_kg_kg","AE_P_kg_kg","AE_K_kg_kg"])
ae_wide.to_csv(TABLES/"1g_agronomic_efficiency_by_site.csv",index=False)

fig=plt.figure(figsize=(18,15))
outer=GridSpec(3,3,figure=fig,hspace=.24,wspace=.12)
last=None

for i,year in enumerate(YEARS):
    for j,(nutrient,_,_) in enumerate(specs):
        inner=GridSpecFromSubplotSpec(2,1,subplot_spec=outer[i,j],height_ratios=[.42,1.35],hspace=.07)
        r=response.loc[(response["year"].eq(year))&(response["nutrient"].eq(nutrient))].copy()

        axv=fig.add_subplot(inner[0,0])
        violin_single(axv,r["yield_response_t_ha"] if not r.empty else [],label="",color="#555555")
        axv.axhline(0,color="black",linestyle="--",linewidth=.7)
        axv.set_xticks([])
        if i==0:
            axv.set_title(f"Yield response to {nutrient}",fontsize=12,fontweight="semibold")
        if j==0:
            axv.set_ylabel(f"{year}\nResponse")

        axm=fig.add_subplot(inner[1,0])
        last=response_map_on_ax(axm,r,boundary,response_col="yield_response_t_ha",fixed_districts=fixed_districts)
        if axm.axison:
            axm.set_xlabel("Longitude")
            if j==0:
                axm.set_ylabel("Latitude")

if last is not None:
    cax=fig.add_axes([.30,.035,.40,.018])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Yield response to nutrient (t ha$^{-1}$)")

fig.suptitle("Nutrient yield response: year × nutrient",fontsize=16,fontweight="semibold",y=.995)
fig.subplots_adjust(bottom=.08,top=.965)
save(fig,"1g_nutrient_yield_response.png")

fig=plt.figure(figsize=(18,15))
outer=GridSpec(3,3,figure=fig,hspace=.24,wspace=.12)
scatters={}

for i,year in enumerate(YEARS):
    for j,(nutrient,_,_) in enumerate(specs):
        inner=GridSpecFromSubplotSpec(2,1,subplot_spec=outer[i,j],height_ratios=[.42,1.35],hspace=.07)
        col=f"AE_{nutrient}_kg_kg"
        r=response.loc[(response["year"].eq(year))&(response["nutrient"].eq(nutrient))].copy()

        axv=fig.add_subplot(inner[0,0])
        violin_single(axv,r[col] if (not r.empty and col in r.columns) else [],label="",color="#555555")
        axv.set_xticks([])
        if i==0:
            axv.set_title(f"AE-{nutrient}",fontsize=12,fontweight="semibold")
        if j==0:
            axv.set_ylabel(f"{year}\nAE")

        axm=fig.add_subplot(inner[1,0])
        sc=ae_map_on_ax(axm,r,nutrient,boundary,fixed_districts=fixed_districts)
        if sc is not None:
            scatters[nutrient]=sc
        if axm.axison:
            axm.set_xlabel("Longitude")
            if j==0:
                axm.set_ylabel("Latitude")

positions={"N":[.08,.035,.25,.018],"P":[.375,.035,.25,.018],"K":[.67,.035,.25,.018]}
for nutrient,_,_ in specs:
    if nutrient in scatters:
        cax=fig.add_axes(positions[nutrient])
        cb=fig.colorbar(scatters[nutrient],cax=cax,orientation="horizontal")
        cb.set_label(f"AE-{nutrient} (kg grain kg$^{{-1}}$ applied {nutrient})")

fig.suptitle("Agronomic efficiency: year × nutrient",fontsize=16,fontweight="semibold",y=.995)
fig.subplots_adjust(bottom=.08,top=.965)
save(fig,"1g_agronomic_efficiency.png")

cols=[c for c in ["AE_N_kg_kg","AE_P_kg_kg","AE_K_kg_kg"] if c in ae_wide.columns]
if cols:
    print(ae_wide.groupby("year")[cols].mean())
