from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.patches import Patch

ROOT = Path(r"D:\dss\SOIL ADVISORY")
DATA = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize" / "harmonised" / "nsaf_maize_key_variables.csv"
BOUNDARY = ROOT / "Data" / "boundary" / "ward_level_boundary.gpkg"

FIGURES = ROOT / "outputs" / "figures"
MAPS = ROOT / "outputs" / "maps"
TABLES = ROOT / "outputs" / "tables"
for p in [FIGURES, MAPS, TABLES]:
    p.mkdir(parents=True, exist_ok=True)

DISTRICT_ORDER = ["Doti","Surkhet","Salyan","Dang","Palpa","Makwanpur","Nuwakot","Kavre"]

ALIASES = {
    "doti":"Doti","surkhet":"Surkhet","salyan":"Salyan","dang":"Dang",
    "palpa":"Palpa","makwanpur":"Makwanpur","makawanpur":"Makwanpur",
    "nuwakot":"Nuwakot","kavre":"Kavre","kavrepalanchok":"Kavre",
    "kavrepalanchowk":"Kavre","kabhrepalanchok":"Kavre","kabhrepalanchowk":"Kavre"
}

COLORS = {
    "000":"#7F7F7F",
    "0PK":"#009E73",
    "minusP":"#E69F00",
    "minusK":"#CC79A7",
    "GR":"#0072B2",
    "N60":"#A6CEE3",
    "N180":"#6A51A3",
    "N210":"#3F007D",
    "Timing":"#9467BD",
    "PCU120":"#1B9E77",
    "PCU60":"#66A61E",
    "UDP":"#7570B3",
    "FYM60":"#D95F02",
    "Hybrid":"#0072B2",
    "OPV":"#D95F02",
}

def norm_district(x):
    if pd.isna(x):
        return np.nan
    k = re.sub(r"[^a-z0-9]+","",str(x).lower())
    return ALIASES.get(k,str(x).strip())

def load_data():
    df = pd.read_csv(DATA)
    needed = [
        "year","study","dataset_type","district","site","latitude","longitude",
        "variety","variety_group","treatment_code","treatment","treatment_role",
        "N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha","yield_14pct_kg_ha"
    ]
    miss = [c for c in needed if c not in df.columns]
    if miss:
        raise ValueError("Run final 0a ingest first. Missing columns: " + ", ".join(miss))
    for c in ["year","latitude","longitude","N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha","yield_14pct_kg_ha"]:
        df[c] = pd.to_numeric(df[c],errors="coerce")
    df["district"] = df["district"].map(norm_district)
    df["yield_t_ha"] = df["yield_14pct_kg_ha"]/1000.0
    return df

def load_boundary():
    b = gpd.read_file(BOUNDARY)
    if b.crs is None:
        raise ValueError("Boundary CRS missing")
    b = b.to_crs(4326)
    dcol = next((c for c in ["district","District","DISTRICT","dist_name","DIST_NAME","NAME_2"] if c in b.columns),None)
    if dcol is None:
        raise ValueError("District name field not found in boundary")
    b["_district"] = b[dcol].map(norm_district)
    return b

def relevant_districts(df):
    have = set(df["district"].dropna())
    return [d for d in DISTRICT_ORDER if d in have]

def site_summary(df, group_cols):
    return (
        df.groupby(group_cols,dropna=False)
          .agg(
              mean_yield_t_ha=("yield_t_ha","mean"),
              N_rate_kg_ha=("N_rate_kg_ha","mean"),
              latitude=("latitude","mean"),
              longitude=("longitude","mean"),
              n=("yield_t_ha","count")
          )
          .reset_index()
    )

def district_violin(
    df, group_col, order, labels, colors, title, outfile,
    value_col="yield_t_ha", ylabel="Maize grain yield (t ha$^{-1}$)",
    include_overall=True
):
    districts = relevant_districts(df)
    cats = (["Overall"] if include_overall else []) + districts
    fig, ax = plt.subplots(figsize=(max(13,1.45*len(cats)),7.2))
    width = 0.72/max(len(order),1)
    offsets = np.linspace(-0.32,0.32,len(order)) if len(order)>1 else [0]
    rng = np.random.default_rng(42)

    handles=[]
    for gi,g in enumerate(order):
        col = colors.get(g,"#4C78A8")
        handles.append(Patch(facecolor=col,edgecolor=col,alpha=.45,label=labels.get(g,g)))
        for ci,cat in enumerate(cats):
            sub = df if cat=="Overall" else df.loc[df["district"].eq(cat)]
            vals = pd.to_numeric(sub.loc[sub[group_col].eq(g),value_col],errors="coerce").dropna().to_numpy()
            if len(vals)==0:
                continue
            x = ci + offsets[gi]
            vp = ax.violinplot([vals],positions=[x],widths=width*1.75,showmeans=False,showmedians=True,showextrema=False)
            body=vp["bodies"][0]
            body.set_facecolor(col); body.set_edgecolor(col); body.set_alpha(.22)
            vp["cmedians"].set_color(col); vp["cmedians"].set_linewidth(1.4)
            ax.scatter(
                np.full(len(vals),x)+rng.uniform(-width*.35,width*.35,len(vals)),
                vals,s=18,color=col,alpha=.78,edgecolors="none",zorder=5
            )

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats,rotation=35,ha="right")
    if include_overall and cats:
        ax.axvline(.5,color="#9ecae1",linestyle="--",linewidth=.8)
        ax.get_xticklabels()[0].set_fontweight("bold")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Overall and district")
    ax.set_title(title,fontweight="semibold")
    ax.grid(axis="y",alpha=.18)
    ax.legend(handles=handles,title="",ncol=min(len(handles),5),loc="upper center",bbox_to_anchor=(.5,1.13),frameon=False)
    fig.subplots_adjust(left=.07,right=.98,bottom=.18,top=.82)
    fig.savefig(FIGURES/outfile,dpi=300,bbox_inches="tight")
    plt.close(fig)

def boundary_union_extent(boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)]
    minx,miny,maxx,maxy = bb.total_bounds
    dx=max(maxx-minx,.1); dy=max(maxy-miny,.1)
    return (minx-.05*dx,maxx+.05*dx),(miny-.07*dy,maxy+.07*dy)

def draw_base(ax,boundary,districts,xlim,ylim):
    bb=boundary.loc[boundary["_district"].isin(districts)].copy()
    bb.boundary.plot(ax=ax,color=".83",linewidth=.35,zorder=1)
    d=bb[["_district","geometry"]].dissolve(by="_district").reset_index()
    d.boundary.plot(ax=ax,color=".35",linewidth=.8,zorder=2)
    rp=d.geometry.representative_point()
    for name,x,y in zip(d["_district"],rp.x,rp.y):
        ax.annotate(
            name,(x,y),xytext=(5,5),textcoords="offset points",
            fontsize=7.5,bbox=dict(facecolor="white",edgecolor="none",alpha=.6,pad=.4),
            zorder=7
        )
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal",adjustable="box")
    ax.set_xlabel("Longitude (degrees)"); ax.set_ylabel("Latitude (degrees)")

def map_grid(
    df, panel_col, order, labels, value_col, title, outfile,
    cmap="YlGnBu", fixed_vmin=None, fixed_vmax=None
):
    q=df.dropna(subset=["latitude","longitude",value_col]).copy()
    if q.empty:
        print(f"{outfile}: no mappable data")
        return
    boundary=load_boundary()
    districts=relevant_districts(q)
    xlim,ylim=boundary_union_extent(boundary,districts)
    vals=q[value_col].dropna()
    vmin=float(vals.min()) if fixed_vmin is None else fixed_vmin
    vmax=float(vals.max()) if fixed_vmax is None else fixed_vmax
    if vmin==vmax: vmax=vmin+1

    n=len(order); ncol=min(3,n); nrow=int(np.ceil(n/ncol))
    fig,axes=plt.subplots(nrow,ncol,figsize=(5.2*ncol,4.7*nrow),squeeze=False)
    last=None
    for i,g in enumerate(order):
        ax=axes.flat[i]
        sub=q.loc[q[panel_col].eq(g)]
        draw_base(ax,boundary,districts,xlim,ylim)
        if sub.empty:
            ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center",alpha=.6)
        else:
            last=ax.scatter(
                sub["longitude"],sub["latitude"],c=sub[value_col],
                cmap=cmap,vmin=vmin,vmax=vmax,s=56,
                edgecolors="black",linewidths=.25,zorder=5
            )
        ax.set_title(labels.get(g,g),fontweight="semibold")
    for j in range(n,len(axes.flat)):
        axes.flat[j].set_axis_off()
    fig.suptitle(title,fontweight="semibold",fontsize=14)
    if last is not None:
        cax=fig.add_axes([.30,.045,.40,.022])
        cb=fig.colorbar(last,cax=cax,orientation="horizontal")
        cb.set_label(value_col.replace("_"," "))
    fig.subplots_adjust(left=.06,right=.98,bottom=.12,top=.90,wspace=.17,hspace=.22)
    fig.savefig(MAPS/outfile,dpi=300,bbox_inches="tight")
    plt.close(fig)

def ae_vs_0pk(df, target_roles, target_labels=None):
    """
    AE-N for each target treatment relative to 0PK (N omission):
      AE-N = (Y_target - Y_0PK) * 1000 / target N rate
    The denominator is inorganic N only, taken from N_rate_kg_ha in the harmonised dataframe.
    """
    x=df.loc[df["treatment_role"].isin(list(target_roles)+["n_omission"])].copy()
    base=(
        x.loc[x["treatment_role"].eq("n_omission")]
         .groupby(["year","study","dataset_type","district","site"],dropna=False)
         .agg(y_0PK_t_ha=("yield_t_ha","mean"))
         .reset_index()
    )
    out=[]
    for role in target_roles:
        t=(
            x.loc[x["treatment_role"].eq(role)]
             .groupby(["year","study","dataset_type","district","site"],dropna=False)
             .agg(
                 treatment_yield_t_ha=("yield_t_ha","mean"),
                 N_rate_kg_ha=("N_rate_kg_ha","mean"),
                 latitude=("latitude","mean"),
                 longitude=("longitude","mean")
             )
             .reset_index()
        )
        z=t.merge(base,on=["year","study","dataset_type","district","site"],how="inner")
        z["treatment_role"]=role
        z["yield_response_vs_0PK_t_ha"]=z["treatment_yield_t_ha"]-z["y_0PK_t_ha"]
        z["AE_N_vs_0PK_kg_kg"]=np.where(
            z["N_rate_kg_ha"]>0,
            z["yield_response_vs_0PK_t_ha"]*1000/z["N_rate_kg_ha"],
            np.nan
        )
        z["relative_yield_vs_0PK_pct"]=100*z["treatment_yield_t_ha"]/z["y_0PK_t_ha"]
        out.append(z)
    return pd.concat(out,ignore_index=True) if out else pd.DataFrame()

def demo_variety_summary(df, year):
    q=df.loc[
        df["year"].eq(year)
        & df["dataset_type"].astype(str).str.lower().eq("demo")
        & df["variety_group"].isin(["Hybrid","OPV"])
    ].copy()
    return q
