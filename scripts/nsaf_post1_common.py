from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

ROOT = Path(r"D:\dss\SOIL ADVISORY")
DATA = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize" / "harmonised" / "nsaf_maize_key_variables.csv"
BOUNDARY = ROOT / "Data" / "boundary" / "ward_level_boundary.gpkg"

FIGURES = ROOT / "outputs" / "figures"
TABLES = ROOT / "outputs" / "tables"
FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

DISTRICT_ALIASES = {
    "doti":"Doti","surkhet":"Surkhet","salyan":"Salyan","dang":"Dang",
    "palpa":"Palpa","makwanpur":"Makwanpur","makawanpur":"Makwanpur",
    "nuwakot":"Nuwakot","kavre":"Kavre","kavrepalanchok":"Kavre",
    "kavrepalanchowk":"Kavre","kabhrepalanchok":"Kavre",
    "kabhrepalanchowk":"Kavre","chitwan":"Chitwan"
}

RESPONSE_CMAP = LinearSegmentedColormap.from_list(
    "response_red_yellow_green",
    ["#B2182B","#F4A582","#FFF3A1","#A6D96A","#1A9850"]
)

def norm_district(x):
    if pd.isna(x):
        return np.nan
    k = re.sub(r"[^a-z0-9]+","",str(x).lower())
    return DISTRICT_ALIASES.get(k,str(x).strip())

def load_data():
    df = pd.read_csv(DATA)
    required = {
        "year","study","dataset_type","district","site","latitude","longitude",
        "variety","variety_group","treatment_code","treatment_role","treatment",
        "N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha","yield_14pct_kg_ha"
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Run 0a first; missing: " + ", ".join(missing))
    for c in ["year","latitude","longitude","N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha","yield_14pct_kg_ha"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["district"] = df["district"].map(norm_district)
    df["yield_t_ha"] = df["yield_14pct_kg_ha"] / 1000.0
    return df

def load_boundary():
    b = gpd.read_file(BOUNDARY)
    if b.crs is None:
        raise ValueError("Boundary CRS is missing.")
    b = b.to_crs(4326)
    dcol = next((c for c in ["district","District","DISTRICT","dist_name","DIST_NAME","NAME_2"] if c in b.columns), None)
    if dcol is None:
        raise ValueError("District field not found in boundary.")
    b["_district"] = b[dcol].map(norm_district)
    return b

def site_means(q):
    return (
        q.groupby(
            ["year","study","dataset_type","district","site","variety_group",
             "treatment_code","treatment_role","N_rate_kg_ha"],
            dropna=False
        )
        .agg(
            mean_yield_t_ha=("yield_t_ha","mean"),
            latitude=("latitude","mean"),
            longitude=("longitude","mean"),
            n=("yield_t_ha","count")
        )
        .reset_index()
    )

def district_labels(boundary, districts):
    d = (
        boundary.loc[boundary["_district"].isin(districts),["_district","geometry"]]
        .dissolve(by="_district")
        .reset_index()
    )
    if d.empty:
        return pd.DataFrame(columns=["district","x","y"])
    p = d.geometry.representative_point()
    return pd.DataFrame({"district":d["_district"],"x":p.x,"y":p.y})

def draw_base(ax, boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    if bb.empty:
        return
    bb.boundary.plot(ax=ax,color="0.82",linewidth=.35,zorder=1)
    (
        bb[["_district","geometry"]]
        .dissolve(by="_district")
        .boundary.plot(ax=ax,color="0.35",linewidth=.9,zorder=2)
    )
    lab = district_labels(boundary,districts)
    for _,r in lab.iterrows():
        ax.annotate(
            r["district"],xy=(r["x"],r["y"]),xytext=(6,6),
            textcoords="offset points",fontsize=8,
            bbox=dict(facecolor="white",edgecolor="none",alpha=.7,pad=.5),
            arrowprops=dict(arrowstyle="-",color="0.4",linewidth=.5),
            zorder=8
        )

def limits(boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    minx,miny,maxx,maxy = bb.total_bounds
    dx=max(maxx-minx,.1); dy=max(maxy-miny,.1)
    return (minx-.05*dx,maxx+.05*dx),(miny-.08*dy,maxy+.08*dy)

def violin(ax, q, roles, labels, colors=None):
    data=[]; pos=[]; labs=[]; found=[]
    for i,r in enumerate(roles,start=1):
        v=q.loc[q["treatment_role"].eq(r),"yield_t_ha"].dropna().to_numpy()
        if len(v):
            data.append(v); pos.append(i); labs.append(labels.get(r,r)); found.append(r)
    if not data:
        ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center")
        return
    vp=ax.violinplot(data,positions=pos,widths=.72,showmeans=False,showmedians=True,showextrema=False)
    rng=np.random.default_rng(42)
    for body,r in zip(vp["bodies"],found):
        c=(colors or {}).get(r,"#4C78A8")
        body.set_facecolor(c); body.set_edgecolor(c); body.set_alpha(.22)
    vp["cmedians"].set_color("black")
    for x,v,r in zip(pos,data,found):
        c=(colors or {}).get(r,"#4C78A8")
        ax.scatter(np.full(len(v),x)+rng.uniform(-.10,.10,len(v)),v,s=19,color=c,alpha=.8,edgecolors="none",zorder=5)
    ax.set_xticks(pos); ax.set_xticklabels(labs,rotation=28,ha="right",fontsize=9)
    ax.set_ylabel("Maize grain yield (t ha$^{-1}$)")
    ax.grid(axis="y",alpha=.18)

def pair_estimate(q, treatment_role=None, comparator_role=None, treatment_code=None, comparator_code=None):
    """
    Site-level paired contrast using the harmonised dataframe.

    Explicit treatment codes are preferred for fixed experimental contrasts.
    Roles remain available for strategy blocks where codes are not required.
    """
    x = q.copy()

    if treatment_code is not None and comparator_code is not None:
        tc = str(treatment_code).upper()
        cc = str(comparator_code).upper()
        code = x["treatment_code"].astype(str).str.upper()
        x["contrast_group"] = np.where(
            code.eq(tc), "treatment",
            np.where(code.eq(cc), "comparator", pd.NA)
        )
    else:
        x["contrast_group"] = np.where(
            x["treatment_role"].eq(treatment_role), "treatment",
            np.where(x["treatment_role"].eq(comparator_role), "comparator", pd.NA)
        )

    x = x.loc[x["contrast_group"].notna()].copy()

    empty_cols = [
        "year","study","dataset_type","district","site","variety_group",
        "latitude","longitude","treatment_yield_t_ha","comparator_yield_t_ha",
        "yield_response_t_ha","relative_yield_pct"
    ]
    if x.empty:
        return pd.DataFrame(columns=empty_cols)

    s = (
        x.groupby(
            ["year","study","dataset_type","district","site","variety_group","contrast_group"],
            dropna=False
        )
        .agg(
            mean_yield_t_ha=("yield_t_ha","mean"),
            latitude=("latitude","mean"),
            longitude=("longitude","mean")
        )
        .reset_index()
    )

    w = (
        s.pivot_table(
            index=["year","study","dataset_type","district","site","variety_group"],
            columns="contrast_group",
            values="mean_yield_t_ha",
            aggfunc="first"
        )
        .reset_index()
    )

    if "treatment" not in w.columns:
        w["treatment"] = np.nan
    if "comparator" not in w.columns:
        w["comparator"] = np.nan

    coords = (
        s.groupby(
            ["year","study","dataset_type","district","site","variety_group"],
            dropna=False
        )
        .agg(latitude=("latitude","mean"), longitude=("longitude","mean"))
        .reset_index()
    )

    w = w.merge(
        coords,
        on=["year","study","dataset_type","district","site","variety_group"],
        how="left"
    )

    w = w.rename(columns={
        "treatment":"treatment_yield_t_ha",
        "comparator":"comparator_yield_t_ha"
    })

    w["yield_response_t_ha"] = (
        w["treatment_yield_t_ha"] - w["comparator_yield_t_ha"]
    )
    w["relative_yield_pct"] = (
        100.0 * w["treatment_yield_t_ha"] / w["comparator_yield_t_ha"]
    )

    return w


def response_map(ax, est, boundary, title):
    required = {"latitude","longitude","yield_response_t_ha"}
    if est is None or est.empty or not required.issubset(est.columns):
        ax.text(
            .5,.5,"No paired site estimate",
            transform=ax.transAxes,ha="center",va="center",alpha=.65
        )
        ax.set_axis_off()
        return None

    q = est.dropna(subset=["latitude","longitude","yield_response_t_ha"]).copy()
    if q.empty:
        ax.text(
            .5,.5,"No paired site estimate",
            transform=ax.transAxes,ha="center",va="center",alpha=.65
        )
        ax.set_axis_off()
        return None

    districts = set(q["district"].dropna())
    draw_base(ax,boundary,districts)
    xlim,ylim = limits(boundary,districts)

    vmax = max(
        abs(float(q["yield_response_t_ha"].min())),
        abs(float(q["yield_response_t_ha"].max())),
        .1
    )
    norm = TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax)

    sc = ax.scatter(
        q["longitude"],q["latitude"],
        c=q["yield_response_t_ha"],
        cmap=RESPONSE_CMAP,norm=norm,
        s=62,edgecolors="black",linewidths=.25,zorder=5
    )

    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal",adjustable="box")
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title(title,fontsize=11,fontweight="semibold")
    return sc


def pair_stage(
    stage, year, dataset_type,
    treatment_role, comparator_role,
    treatment_label, comparator_label,
    title, study_contains=None,
    treatment_code=None, comparator_code=None
):
    df = load_data()

    q = df.loc[
        df["year"].eq(year)
        & df["dataset_type"].astype(str).str.lower().eq(dataset_type.lower())
    ].copy()

    if study_contains:
        q = q.loc[
            q["study"].astype(str).str.contains(study_contains,case=False,na=False)
        ].copy()

    if treatment_code is not None and comparator_code is not None:
        codes = {str(treatment_code).upper(), str(comparator_code).upper()}
        q = q.loc[q["treatment_code"].astype(str).str.upper().isin(codes)].copy()
    else:
        q = q.loc[q["treatment_role"].isin([treatment_role,comparator_role])].copy()

    est = pair_estimate(
        q,
        treatment_role=treatment_role,
        comparator_role=comparator_role,
        treatment_code=treatment_code,
        comparator_code=comparator_code
    )
    est.to_csv(TABLES/f"{stage}_estimates.csv",index=False)

    if q.empty:
        print(f"{stage}: no matching observations; estimate table written empty.")
        return

    qp = q.copy()
    if treatment_code is not None and comparator_code is not None:
        code = qp["treatment_code"].astype(str).str.upper()
        qp["treatment_role"] = np.where(
            code.eq(str(treatment_code).upper()), "treatment", "comparator"
        )
    else:
        qp["treatment_role"] = np.where(
            qp["treatment_role"].eq(treatment_role),"treatment","comparator"
        )

    fig = plt.figure(figsize=(13.5,6.8))
    gs = GridSpec(1,2,figure=fig,width_ratios=[.9,1.35],wspace=.18)

    ax1 = fig.add_subplot(gs[0,0])
    violin(
        ax1,qp,["comparator","treatment"],
        {"comparator":comparator_label,"treatment":treatment_label},
        {"comparator":"#7F7F7F","treatment":"#0072B2"}
    )
    ax1.set_title("Yield distribution",fontsize=11,fontweight="semibold")

    ax2 = fig.add_subplot(gs[0,1])
    sc = response_map(ax2,est,load_boundary(),"Site-level yield response")
    if sc is not None:
        cb = fig.colorbar(sc,ax=ax2,orientation="horizontal",fraction=.045,pad=.10)
        cb.set_label("Yield response: treatment − comparator (t ha$^{-1}$)")

    fig.suptitle(title,fontsize=14,fontweight="semibold")
    fig.subplots_adjust(left=.07,right=.97,bottom=.12,top=.90,wspace=.22)
    fig.savefig(FIGURES/f"{stage}.png",dpi=300,bbox_inches="tight")
    plt.close(fig)


def strategy_stage(stage, year, variety_group, roles, labels, reference_role, title):
    df=load_data()
    q=df.loc[
        df["year"].eq(year)
        & df["dataset_type"].astype(str).str.lower().eq("demo")
        & df["variety_group"].astype(str).str.lower().eq(variety_group.lower())
        & df["treatment_role"].isin(roles)
    ].copy()

    all_est=[]
    for r in roles:
        if r==reference_role:
            continue
        e=pair_estimate(q,treatment_role=r,comparator_role=reference_role)
        if not e.empty:
            e["strategy_role"]=r
            all_est.append(e)
    est=pd.concat(all_est,ignore_index=True) if all_est else pd.DataFrame()
    est.to_csv(TABLES/f"{stage}_estimates.csv",index=False)

    fig=plt.figure(figsize=(17,8.5))
    outer=GridSpec(2,1,figure=fig,height_ratios=[.85,1.45],hspace=.28)

    axv=fig.add_subplot(outer[0,0])
    colors={r:"#0072B2" if r==reference_role else "#4C78A8" for r in roles}
    violin(axv,q,roles,labels,colors)
    axv.set_title("Yield distribution",fontsize=11,fontweight="semibold")

    maps=GridSpecFromSubplotSpec(1,max(len(roles)-1,1),subplot_spec=outer[1,0],wspace=.16)
    boundary=load_boundary()
    last=None
    for j,r in enumerate([x for x in roles if x!=reference_role]):
        ax=fig.add_subplot(maps[0,j])
        e=est.loc[est["strategy_role"].eq(r)].copy() if not est.empty else pd.DataFrame()
        last=response_map(ax,e,boundary,labels[r])
    if last is not None:
        cax=fig.add_axes([.30,.055,.40,.022])
        cb=fig.colorbar(last,cax=cax,orientation="horizontal")
        cb.set_label("Yield response relative to reference (t ha$^{-1}$)")

    fig.suptitle(title,fontsize=14,fontweight="semibold")
    fig.subplots_adjust(bottom=.13,top=.93)
    fig.savefig(FIGURES/f"{stage}.png",dpi=300,bbox_inches="tight")
    plt.close(fig)
