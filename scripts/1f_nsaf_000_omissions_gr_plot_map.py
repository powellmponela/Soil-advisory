from nsaf_stage1_common import *

df=trial_only(load_data())
boundary=load_boundary()

roles=["soil_background","n_omission","p_omission","k_omission","government_recommendation"]
labels={
    "soil_background":"Unfertilized control\n(0–0–0)",
    "n_omission":"N omission\n(−N)",
    "p_omission":"P omission\n(−P)",
    "k_omission":"K omission\n(−K)",
    "government_recommendation":"Government\nrecommendation (GR)",
}

all_obs=[]

for year in YEARS:
    q=df.loc[df["year"].eq(year)&df["treatment_role"].isin(roles)].copy()
    all_obs.append(q)
    available=[r for r in roles if q.loc[q["treatment_role"].eq(r),"yield_t_ha"].notna().any()]
    s=site_means(q)
    fixed_districts=set(s["district"].dropna())
    vals=s["mean_yield_t_ha"].dropna()
    vmin=float(vals.min()) if len(vals) else 0
    vmax=float(vals.max()) if len(vals) else 1

    fig=plt.figure(figsize=(18,8.8))
    outer=GridSpec(2,1,figure=fig,height_ratios=[.95,1.35],hspace=.28)

    axv=fig.add_subplot(outer[0,0])
    violin_grouped(axv,q,available,labels)
    axv.set_ylabel("Maize grain yield (t ha$^{-1}$)")
    axv.set_title(f"{year}: treatment yield distributions",fontsize=12,fontweight="semibold")

    maps=GridSpecFromSubplotSpec(1,len(available),subplot_spec=outer[1,0],wspace=.15)
    last=None
    for j,role in enumerate(available):
        axm=fig.add_subplot(maps[0,j])
        ss=s.loc[s["treatment_role"].eq(role)]
        last=yield_map_on_ax(axm,ss,boundary,title=labels[role].replace("\n"," "),vmin=vmin,vmax=vmax,fixed_districts=fixed_districts)
        axm.set_xlabel("Longitude")
        if j==0:
            axm.set_ylabel("Latitude")

    if last is not None:
        cax=fig.add_axes([.30,.055,.40,.022])
        cb=fig.colorbar(last,cax=cax,orientation="horizontal")
        cb.set_label("Maize grain yield (t ha$^{-1}$)")

    fig.suptitle(
        f"{year}: unfertilized control, nutrient omissions and government recommendation",
        fontsize=15,fontweight="semibold",y=.98
    )
    fig.subplots_adjust(bottom=.13,top=.92)
    save(fig,f"1f_000_omissions_gr_{year}.png")

pd.concat(all_obs,ignore_index=True).to_csv(TABLES/"1f_000_omissions_gr_observations.csv",index=False)
