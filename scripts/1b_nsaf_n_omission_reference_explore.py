from nsaf_stage1_common import *

df=trial_only(load_data())
boundary=load_boundary()
roles=["soil_background","n_omission"]
stage_q=df.loc[df["treatment_role"].isin(roles)].copy()
fixed_districts=set(stage_q["district"].dropna())
labels={
    "soil_background":"Unfertilized control (0–0–0)",
    "n_omission":"N omission (−N): N0–P60–K40",
}

fig=plt.figure(figsize=(16,9))
gs=GridSpec(2,3,figure=fig,height_ratios=[.78,1.38],hspace=.30,wspace=.16)
last=None
all_resp=[]

for j,year in enumerate(YEARS):
    q=df.loc[df["year"].eq(year)&df["treatment_role"].isin(roles)].copy()

    axv=fig.add_subplot(gs[0,j])
    violin_grouped(axv,q,roles,labels)
    axv.set_title(str(year),fontsize=12,fontweight="semibold")
    if j==0:
        axv.set_ylabel("Maize grain yield (t ha$^{-1}$)")

    resp=paired_site_response(q,"n_omission","soil_background")
    if not resp.empty:
        resp["year"]=year
        all_resp.append(resp)

    axm=fig.add_subplot(gs[1,j])
    last=response_map_on_ax(axm,resp,boundary,fixed_districts=fixed_districts,title=f"{year}: Yield response to P+K")
    axm.set_xlabel("Longitude (degrees)")
    if j==0:
        axm.set_ylabel("Latitude (degrees)")

if last is not None:
    cax=fig.add_axes([.30,.055,.40,.022])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Yield response to P+K (t ha$^{-1}$)")

fig.suptitle("Yield response to P+K: omission treatment compared with unfertilized control",fontsize=15,fontweight="semibold",y=.98)
fig.subplots_adjust(bottom=.13,top=.92)
save(fig,"1b_nsaf_n_omission_reference_explore.png")

if all_resp:
    pd.concat(all_resp,ignore_index=True).to_csv(TABLES/"1b_nsaf_n_omission_reference_explore_site_response.csv",index=False)
