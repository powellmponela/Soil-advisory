from nsaf_post1_common import *

df=load_data()
roles=["n_omission","n_rate_60","government_recommendation","n_rate_180","n_rate_210"]
rates={"n_omission":0,"n_rate_60":60,"government_recommendation":120,"n_rate_180":180,"n_rate_210":210}
labels={r:f"{n} kg N ha$^{{-1}}$" for r,n in rates.items()}

q=df.loc[
    df["year"].eq(2017)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(roles)
].copy()

s=site_means(q)
s["N_rate_kg_ha"]=s["treatment_role"].map(rates)
s.to_csv(TABLES/"2a_2017_n_rate_site_means.csv",index=False)

# Wide site table and agronomic estimates
w=s.pivot_table(
    index=["year","district","site","latitude","longitude"],
    columns="N_rate_kg_ha",values="mean_yield_t_ha",aggfunc="first"
).reset_index()

for n in [60,120,180,210]:
    if 0 in w.columns and n in w.columns:
        w[f"AE_N_{n}_kg_kg"]=(w[n]-w[0])*1000/n

for lo,hi in [(0,60),(60,120),(120,180),(180,210)]:
    if lo in w.columns and hi in w.columns:
        w[f"marginal_yield_response_{lo}_{hi}_t_ha"]=w[hi]-w[lo]
        w[f"marginal_response_{lo}_{hi}_kg_kg_N"]=(w[hi]-w[lo])*1000/(hi-lo)

w.to_csv(TABLES/"2a_2017_n_rate_estimates.csv",index=False)

best=(
    s.dropna(subset=["mean_yield_t_ha","N_rate_kg_ha"])
    .sort_values(["district","site","mean_yield_t_ha"])
    .groupby(["district","site"],as_index=False)
    .tail(1)
)
best.to_csv(TABLES/"2a_2017_best_observed_n_rate.csv",index=False)

fig=plt.figure(figsize=(15,7.5))
gs=GridSpec(1,2,figure=fig,width_ratios=[1.0,1.15],wspace=.18)

ax1=fig.add_subplot(gs[0,0])
for (district,site),g in s.groupby(["district","site"],dropna=False):
    g=g.sort_values("N_rate_kg_ha")
    ax1.plot(g["N_rate_kg_ha"],g["mean_yield_t_ha"],marker="o",linewidth=1,alpha=.55)
ax1.set_xticks([0,60,120,180,210])
ax1.set_xlabel("N rate (kg N ha$^{-1}$)")
ax1.set_ylabel("Maize grain yield (t ha$^{-1}$)")
ax1.set_title("Site-level N-response curves",fontweight="semibold")
ax1.grid(alpha=.18)

ax2=fig.add_subplot(gs[0,1])
boundary=load_boundary()
districts=set(best["district"].dropna())
draw_base(ax2,boundary,districts)
xlim,ylim=limits(boundary,districts)
sc=ax2.scatter(
    best["longitude"],best["latitude"],c=best["N_rate_kg_ha"],
    cmap="YlGnBu",vmin=0,vmax=210,s=65,edgecolors="black",linewidths=.25,zorder=5
)
ax2.set_xlim(*xlim); ax2.set_ylim(*ylim); ax2.set_aspect("equal",adjustable="box")
ax2.set_xlabel("Longitude (degrees)"); ax2.set_ylabel("Latitude (degrees)")
ax2.set_title("Tested N rate with highest observed site yield",fontweight="semibold")
cb=fig.colorbar(sc,ax=ax2,orientation="horizontal",fraction=.045,pad=.10)
cb.set_ticks([0,60,120,180,210]); cb.set_label("N rate (kg N ha$^{-1}$)")

fig.suptitle("2017 N-rate response under fixed P60-K40",fontsize=14,fontweight="semibold")
fig.subplots_adjust(left=.07,right=.97,bottom=.12,top=.90,wspace=.22)
fig.savefig(FIGURES/"2a_2017_n_rate_response.png",dpi=300,bbox_inches="tight")
plt.close(fig)
