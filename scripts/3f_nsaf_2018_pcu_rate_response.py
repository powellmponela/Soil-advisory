from nsaf_post1_common import *

df=load_data()
q=df.loc[
    df["year"].eq(2018)
    & df["dataset_type"].astype(str).str.lower().eq("trial")
    & df["treatment_role"].isin(["pcu_half_n","pcu_full_n"])
].copy()

est=pair_estimate(q,treatment_code="2",comparator_code="3")
if not est.empty:
    est["marginal_yield_response_t_ha"]=est["yield_response_t_ha"]
    est["marginal_response_kg_kg_N"]=est["yield_response_t_ha"]*1000/60.0
est.to_csv(TABLES/"3f_2018_pcu_rate_estimates.csv",index=False)

fig=plt.figure(figsize=(13.5,6.8))
gs=GridSpec(1,2,figure=fig,width_ratios=[.9,1.35],wspace=.18)
ax1=fig.add_subplot(gs[0,0])
violin(
    ax1,q,["pcu_half_n","pcu_full_n"],
    {"pcu_half_n":"PCU N60","pcu_full_n":"PCU N120"},
    {"pcu_half_n":"#66A61E","pcu_full_n":"#1B9E77"}
)
ax1.set_title("PCU N-rate yield distribution",fontweight="semibold")
ax2=fig.add_subplot(gs[0,1])
sc=response_map(ax2,est,load_boundary(),"Marginal yield response: N60 to N120")
if sc is not None:
    cb=fig.colorbar(sc,ax=ax2,orientation="horizontal",fraction=.045,pad=.10)
    cb.set_label("Marginal yield response (t ha$^{-1}$)")
fig.suptitle("2018 PCU N-rate response",fontsize=14,fontweight="semibold")
fig.subplots_adjust(left=.07,right=.97,bottom=.12,top=.90,wspace=.22)
fig.savefig(FIGURES/"3f_2018_pcu_rate_response.png",dpi=300,bbox_inches="tight")
plt.close(fig)
