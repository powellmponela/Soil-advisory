from nsaf_compare_common import *

df=load_data()

# 2018: descriptive Hybrid vs OPV only. Farmers' seed is retained in the saved
# full summary but excluded from the requested OPV-Hybrid juxtaposition.
all18=df.loc[
    df["year"].eq(2018)
    & df["dataset_type"].astype(str).str.lower().eq("demo")
].copy()
all18.to_csv(TABLES/"4a_2018_demo_all_observations.csv",index=False)
q18=all18.loc[all18["variety_group"].isin(["Hybrid","OPV"])].copy()

district_violin(
    q18,"variety_group",["Hybrid","OPV"],
    {"Hybrid":"Hybrid","OPV":"OPV"},COLORS,
    "2018 Demo: Hybrid vs OPV across districts",
    "4a_2018_demo_hybrid_vs_opv.png"
)

s18=site_summary(q18,["year","district","site","variety_group"])
map_grid(
    s18,"variety_group",["Hybrid","OPV"],
    {"Hybrid":"Hybrid","OPV":"OPV"},"mean_yield_t_ha",
    "2018 Demo: Hybrid vs OPV — site mean yield",
    "4a_2018_demo_hybrid_vs_opv_maps.png"
)

# 2019: compare Hybrid and OPV within matched management strategies.
q19=df.loc[
    df["year"].eq(2019)
    & df["dataset_type"].astype(str).str.lower().eq("demo")
    & df["variety_group"].isin(["Hybrid","OPV"])
].copy()

def strategy_from_role(r):
    s=str(r)
    for suff in ["_hybrid","_opv"]:
        if s.endswith(suff):
            s=s[:-len(suff)]
    return s.replace("demo_","")

q19["strategy"]=q19["treatment_role"].map(strategy_from_role)
strategy_labels={
    "gr":"GR",
    "fym":"FYM + full NPK",
    "zn":"Zn + full NPK",
    "pcu_half_n":"PCU N60",
    "udp_reduced_n":"UDP reduced N"
}
q19.to_csv(TABLES/"4b_2019_demo_hybrid_opv_observations.csv",index=False)

strategies=[s for s in ["gr","fym","zn","pcu_half_n","udp_reduced_n"] if (q19["strategy"]==s).any()]
fig,axes=plt.subplots(len(strategies),1,figsize=(14,5.2*len(strategies)),squeeze=False)
for i,s in enumerate(strategies):
    sub=q19.loc[q19["strategy"].eq(s)].copy()
    # local district violin rendered into a temporary style manually
    ax=axes[i,0]
    districts=relevant_districts(sub)
    cats=["Overall"]+districts
    groups=["Hybrid","OPV"]
    offsets=[-.17,.17]
    rng=np.random.default_rng(42+i)
    for gi,g in enumerate(groups):
        for ci,cat in enumerate(cats):
            xsub=sub if cat=="Overall" else sub.loc[sub["district"].eq(cat)]
            vals=xsub.loc[xsub["variety_group"].eq(g),"yield_t_ha"].dropna().to_numpy()
            if not len(vals): continue
            x=ci+offsets[gi]
            vp=ax.violinplot([vals],positions=[x],widths=.30,showmeans=False,showmedians=True,showextrema=False)
            body=vp["bodies"][0]; body.set_facecolor(COLORS[g]); body.set_edgecolor(COLORS[g]); body.set_alpha(.22)
            vp["cmedians"].set_color(COLORS[g])
            ax.scatter(np.full(len(vals),x)+rng.uniform(-.05,.05,len(vals)),vals,s=17,color=COLORS[g],alpha=.78,edgecolors="none")
    ax.set_xticks(range(len(cats))); ax.set_xticklabels(cats,rotation=35,ha="right")
    ax.axvline(.5,color="#9ecae1",linestyle="--",linewidth=.8)
    ax.set_ylabel("Maize grain yield (t ha$^{-1}$)")
    ax.set_title(strategy_labels.get(s,s),fontweight="semibold")
    ax.grid(axis="y",alpha=.18)
axes[0,0].legend(
    handles=[Patch(facecolor=COLORS["Hybrid"],alpha=.45,label="Hybrid"),
             Patch(facecolor=COLORS["OPV"],alpha=.45,label="OPV")],
    loc="upper center",bbox_to_anchor=(.5,1.18),ncol=2,frameon=False
)
fig.suptitle("2019 Demo: Hybrid vs OPV across districts and management strategies",fontsize=14,fontweight="semibold")
fig.subplots_adjust(left=.07,right=.98,bottom=.06,top=.95,hspace=.42)
fig.savefig(FIGURES/"4b_2019_demo_hybrid_vs_opv.png",dpi=300,bbox_inches="tight")
plt.close(fig)

# Separate maps: strategy x variety
s19=site_summary(q19,["year","district","site","strategy","variety_group"])
boundary=load_boundary()
districts=relevant_districts(s19)
xlim,ylim=boundary_union_extent(boundary,districts)
vals=s19["mean_yield_t_ha"].dropna()
vmin=float(vals.min()); vmax=float(vals.max())

fig,axes=plt.subplots(len(strategies),2,figsize=(11,4.3*len(strategies)),squeeze=False)
last=None
for i,s in enumerate(strategies):
    for j,v in enumerate(["Hybrid","OPV"]):
        ax=axes[i,j]
        draw_base(ax,boundary,districts,xlim,ylim)
        sub=s19.loc[(s19["strategy"].eq(s))&(s19["variety_group"].eq(v))]
        if sub.empty:
            ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center")
        else:
            last=ax.scatter(sub["longitude"],sub["latitude"],c=sub["mean_yield_t_ha"],
                            cmap="YlGnBu",vmin=vmin,vmax=vmax,s=55,edgecolors="black",linewidths=.25,zorder=5)
        ax.set_title(f"{strategy_labels.get(s,s)} — {v}",fontweight="semibold")
if last is not None:
    cax=fig.add_axes([.30,.025,.40,.015])
    cb=fig.colorbar(last,cax=cax,orientation="horizontal")
    cb.set_label("Maize grain yield (t ha$^{-1}$)")
fig.suptitle("2019 Demo: Hybrid and OPV site mean yield",fontsize=14,fontweight="semibold")
fig.subplots_adjust(left=.07,right=.98,bottom=.06,top=.96,hspace=.28,wspace=.15)
fig.savefig(MAPS/"4b_2019_demo_hybrid_vs_opv_maps.png",dpi=300,bbox_inches="tight")
plt.close(fig)
