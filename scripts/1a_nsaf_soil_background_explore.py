from nsaf_stage1_common import *

df=trial_only(load_data())
q=df.loc[df["treatment_role"].eq("soil_background")].copy()
s=site_means(q)
boundary=load_boundary()
fixed_districts=set(s["district"].dropna())

vals=s["mean_yield_t_ha"].dropna()
vmin=float(vals.min()) if len(vals) else 0
vmax=float(vals.max()) if len(vals) else 1

fig=plt.figure(figsize=(16,9))
gs=GridSpec(2,3,figure=fig,height_ratios=[.72,1.45],hspace=.30,wspace=.16)
last=None

for j,year in enumerate(YEARS):
    qq=q.loc[q["year"].eq(year)]
    axv=fig.add_subplot(gs[0,j])
    violin_single(axv,qq["yield_t_ha"],label="Unfertilized control",color=ROLE_COLORS["soil_background"])
    axv.set_title(str(year),fontsize=12,fontweight="semibold")
    if j==0:
        axv.set_ylabel("Maize grain yield (t ha$^{-1}$)")

    axm=fig.add_subplot(gs[1,j])
    ss=s.loc[s["year"].eq(year)]
    last=yield_map_on_ax(axm,ss,boundary,title=f"{year}: unfertilized control (0–0–0)",vmin=vmin,vmax=vmax,fixed_districts=fixed_districts)
    axm.set_xlabel("Longitude (degrees)")
    if j==0:
        axm.set_ylabel("Latitude (degrees)")

if last is not None:
    cax=fig.add_axes([.30,.055,.40,.022])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Maize grain yield (t ha$^{-1}$)")

fig.suptitle("Unfertilized control (0–0–0): maize grain yield",fontsize=15,fontweight="semibold",y=.98)
fig.subplots_adjust(bottom=.13,top=.92)
save(fig,"1a_soil_background.png")

q.to_csv(TABLES/"1a_soil_background_observations.csv",index=False)
print(q.groupby("year").size())
