from nsaf_post1_common import *

df=load_data()
q=df.loc[
    df["year"].eq(2018)
    & df["dataset_type"].astype(str).str.lower().eq("demo")
].copy()

# Keep 2018 Demo source codes and variety groups as recorded.
summary=site_means(q)
summary.to_csv(TABLES/"4a_2018_demo_site_means.csv",index=False)

roles=list(q["treatment_role"].dropna().drop_duplicates())
labels={}
for r in roles:
    codes=q.loc[q["treatment_role"].eq(r),"treatment_code"].dropna().astype(str).unique()
    labels[r]=codes[0] if len(codes) else r

fig=plt.figure(figsize=(16,8.5))
outer=GridSpec(2,1,figure=fig,height_ratios=[.85,1.45],hspace=.28)
ax=fig.add_subplot(outer[0,0])
violin(ax,q,roles,labels)
ax.set_title("2018 demonstration yield distributions",fontweight="semibold")

maps=GridSpecFromSubplotSpec(1,max(len(roles),1),subplot_spec=outer[1,0],wspace=.16)
boundary=load_boundary()
vals=summary["mean_yield_t_ha"].dropna()
vmin=float(vals.min()) if len(vals) else 0
vmax=float(vals.max()) if len(vals) else 1
last=None

for j,r in enumerate(roles):
    a=fig.add_subplot(maps[0,j])
    s=summary.loc[summary["treatment_role"].eq(r)].dropna(subset=["latitude","longitude","mean_yield_t_ha"])
    if s.empty:
        a.set_axis_off(); continue
    districts=set(s["district"].dropna())
    draw_base(a,boundary,districts)
    xlim,ylim=limits(boundary,districts)
    last=a.scatter(
        s["longitude"],s["latitude"],c=s["mean_yield_t_ha"],
        cmap="YlGnBu",vmin=vmin,vmax=vmax,s=58,edgecolors="black",linewidths=.25,zorder=5
    )
    a.set_xlim(*xlim); a.set_ylim(*ylim); a.set_aspect("equal",adjustable="box")
    a.set_title(labels[r],fontsize=10,fontweight="semibold")
    a.set_xlabel("Longitude")
    if j==0: a.set_ylabel("Latitude")

if last is not None:
    cax=fig.add_axes([.30,.055,.40,.022])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Maize grain yield (t ha$^{-1}$)")

fig.suptitle("2018 maize demonstration",fontsize=14,fontweight="semibold")
fig.subplots_adjust(bottom=.13,top=.93)
fig.savefig(FIGURES/"4a_2018_demo.png",dpi=300,bbox_inches="tight")
plt.close(fig)
