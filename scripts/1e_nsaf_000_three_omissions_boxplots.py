from nsaf_stage1_common import *

df=trial_only(load_data())
boundary=load_boundary()
specs=[
    ("n_omission","N omission (−N)"),
    ("p_omission","P omission (−P)"),
    ("k_omission","K omission (−K)"),
]
q=df.loc[df["treatment_role"].isin([r for r,_ in specs])].copy()
s=site_means(q)
fixed_districts=set(s["district"].dropna())

vals=s["mean_yield_t_ha"].dropna()
vmin=float(vals.min()) if len(vals) else 0
vmax=float(vals.max()) if len(vals) else 1

fig=plt.figure(figsize=(18,15))
outer=GridSpec(3,3,figure=fig,hspace=.24,wspace=.12)
last=None

for i,year in enumerate(YEARS):
    for j,(role,label) in enumerate(specs):
        inner=GridSpecFromSubplotSpec(2,1,subplot_spec=outer[i,j],height_ratios=[.42,1.35],hspace=.07)

        vals_y=q.loc[q["year"].eq(year)&q["treatment_role"].eq(role),"yield_t_ha"]
        axv=fig.add_subplot(inner[0,0])
        violin_single(axv,vals_y,label="",color=ROLE_COLORS[role])
        axv.set_xticks([])
        if i==0:
            axv.set_title(label,fontsize=12,fontweight="semibold")
        if j==0:
            axv.set_ylabel(f"{year}\nYield")

        axm=fig.add_subplot(inner[1,0])
        ss=s.loc[s["year"].eq(year)&s["treatment_role"].eq(role)]
        last=yield_map_on_ax(axm,ss,boundary,vmin=vmin,vmax=vmax,fixed_districts=fixed_districts)
        if axm.axison:
            axm.set_xlabel("Longitude")
            if j==0:
                axm.set_ylabel("Latitude")

if last is not None:
    cax=fig.add_axes([.30,.035,.40,.018])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Yield under nutrient omission (t ha$^{-1}$)")

fig.suptitle("Yield under nutrient omission: year × nutrient",fontsize=16,fontweight="semibold",y=.995)
fig.subplots_adjust(bottom=.08,top=.965)
save(fig,"1e_000_three_omissions.png")

q.to_csv(TABLES/"1e_omission_observations.csv",index=False)
