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
MAPS = ROOT / "outputs" / "maps"
TABLES = ROOT / "outputs" / "tables"

for p in [FIGURES, MAPS, TABLES]:
    p.mkdir(parents=True, exist_ok=True)

ALIASES = {
    "doti":"Doti","surkhet":"Surkhet","salyan":"Salyan","dang":"Dang",
    "palpa":"Palpa","makwanpur":"Makwanpur","makawanpur":"Makwanpur",
    "nuwakot":"Nuwakot","kavre":"Kavre","kavrepalanchok":"Kavre",
    "kavrepalanchowk":"Kavre","kabhrepalanchok":"Kavre",
    "kabhrepalanchowk":"Kavre","chitwan":"Chitwan"
}

ROLE_COLORS = {
    "soil_background":"#7F7F7F",
    "n_omission":"#009E73",
    "p_omission":"#E69F00",
    "k_omission":"#CC79A7",
    "government_recommendation":"#0072B2",
    "n_rate_60":"#A6CEE3",
    "n_rate_180":"#4D4D8C",
    "n_rate_210":"#1F1F4E",
    "micronutrients":"#56B4E9",
    "n_timing_v8":"#17BECF",
    "n_timing_v6_v10":"#9467BD",
    "pcu_full_n":"#1B9E77",
    "pcu_half_n":"#66A61E",
    "udp_reduced_n":"#7570B3",
    "fym_half_n":"#D95F02",
    "demo_gr_hybrid":"#0072B2",
    "demo_fym_hybrid":"#D95F02",
    "demo_zn_hybrid":"#E6AB02",
    "demo_pcu_half_n_hybrid":"#1B9E77",
    "demo_udp_reduced_n_hybrid":"#7570B3",
    "demo_gr_opv":"#0072B2",
    "demo_fym_opv":"#D95F02",
    "demo_zn_opv":"#E6AB02",
    "demo_pcu_half_n_opv":"#1B9E77",
    "demo_udp_reduced_n_opv":"#7570B3",
}

DIFF_CMAP = LinearSegmentedColormap.from_list(
    "response", ["#B2182B", "#F4A582", "#FFF3A1", "#A6D96A", "#1A9850"]
)

def norm_district(x):
    if pd.isna(x):
        return np.nan
    k = re.sub(r"[^a-z0-9]+", "", str(x).lower())
    return ALIASES.get(k, str(x).strip())

def load_data():
    df = pd.read_csv(DATA)
    required = {
        "year","study","dataset_type","district","site",
        "latitude","longitude","treatment_role","treatment_code",
        "yield_14pct_kg_ha"
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError("Run revised 0a first; missing: " + ", ".join(missing))

    for c in ["year","latitude","longitude","yield_14pct_kg_ha"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["district"] = df["district"].map(norm_district)
    df["yield_t_ha"] = df["yield_14pct_kg_ha"] / 1000.0
    return df

def load_boundary():
    b = gpd.read_file(BOUNDARY)
    if b.crs is None:
        raise ValueError("Boundary CRS is missing.")
    b = b.to_crs(4326)

    dcol = next(
        (c for c in ["district","District","DISTRICT","dist_name","DIST_NAME","NAME_2"] if c in b.columns),
        None
    )
    if dcol is None:
        raise ValueError("District field not found in boundary.")

    b["_district"] = b[dcol].map(norm_district)
    return b

def trial_only(df):
    return df.loc[df["dataset_type"].astype(str).str.lower().eq("trial")].copy()

def site_means(q):
    return (
        q.groupby(
            ["year","study","dataset_type","district","site","treatment_role"],
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

def district_label_df(boundary, districts):
    d = (
        boundary.loc[boundary["_district"].isin(districts), ["_district","geometry"]]
        .dissolve(by="_district")
        .reset_index()
    )
    if d.empty:
        return pd.DataFrame(columns=["district","x","y"])
    rp = d.geometry.representative_point()
    return pd.DataFrame({
        "district": d["_district"].values,
        "x": rp.x.values,
        "y": rp.y.values,
    })

def draw_boundary_and_labels(ax, boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    if bb.empty:
        return

    bb.boundary.plot(ax=ax, color="0.82", linewidth=0.35, zorder=1)
    (
        bb[["_district","geometry"]]
        .dissolve(by="_district")
        .boundary.plot(ax=ax, color="0.35", linewidth=0.9, zorder=2)
    )

    labels = district_label_df(boundary, districts)
    for _, r in labels.iterrows():
        ax.annotate(
            r["district"],
            xy=(r["x"], r["y"]),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=8.2,
            ha="left",
            va="bottom",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.55, pad=0.5),
            zorder=8,
        )

def global_limits(boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    if bb.empty:
        return (80.5, 86.0), (27.0, 29.6)
    minx,miny,maxx,maxy = bb.total_bounds
    dx=max(maxx-minx,.1); dy=max(maxy-miny,.1)
    return (minx-.05*dx,maxx+.05*dx), (miny-.08*dy,maxy+.08*dy)

def violin_on_ax(ax, vals, color, label=None):
    vals = pd.Series(vals).dropna().to_numpy()
    if len(vals) == 0:
        ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center",alpha=.55)
        return

    parts = ax.violinplot(
        [vals], positions=[1], widths=.72,
        showmeans=False, showmedians=True, showextrema=False
    )
    body = parts["bodies"][0]
    body.set_facecolor(color)
    body.set_edgecolor(color)
    body.set_alpha(.22)
    body.set_linewidth(1.0)
    parts["cmedians"].set_color("black")
    parts["cmedians"].set_linewidth(1.2)

    rng = np.random.default_rng(42)
    ax.scatter(
        np.ones(len(vals)) + rng.uniform(-.10,.10,len(vals)),
        vals, s=18, color=color, alpha=.78, edgecolors="none", zorder=5
    )

    ax.set_xticks([1])
    ax.set_xticklabels([label or ""], rotation=0)
    ax.grid(axis="y", alpha=.18)

def yield_map_on_ax(ax, s, boundary, title=None, vmin=None, vmax=None, cmap="viridis_r"):
    s = s.dropna(subset=["latitude","longitude","mean_yield_t_ha"]).copy()
    if s.empty:
        ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center",alpha=.55)
        ax.set_axis_off()
        return None

    districts = set(s["district"].dropna())
    draw_boundary_and_labels(ax, boundary, districts)
    xlim, ylim = global_limits(boundary, districts)

    if vmin is None:
        vmin = float(s["mean_yield_t_ha"].min())
    if vmax is None:
        vmax = float(s["mean_yield_t_ha"].max())

    sc = ax.scatter(
        s["longitude"], s["latitude"],
        c=s["mean_yield_t_ha"], cmap=cmap,
        vmin=vmin, vmax=vmax,
        s=55, edgecolors="black", linewidths=.25, zorder=5
    )
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    if title:
        ax.set_title(title, fontsize=10.5, fontweight="semibold")
    return sc

def response_df(q, treatment_role, comparator_role):
    s = site_means(q.loc[q["treatment_role"].isin([treatment_role, comparator_role])])
    w = (
        s.pivot_table(
            index=["year","study","dataset_type","district","site"],
            columns="treatment_role",
            values="mean_yield_t_ha",
            aggfunc="first"
        )
        .reset_index()
    )
    if treatment_role not in w.columns or comparator_role not in w.columns:
        return pd.DataFrame()

    coords = (
        s.groupby(["year","study","dataset_type","district","site"], dropna=False)
        .agg(latitude=("latitude","mean"), longitude=("longitude","mean"))
        .reset_index()
    )
    w = w.merge(coords, on=["year","study","dataset_type","district","site"], how="left")
    w["response_t_ha"] = w[treatment_role] - w[comparator_role]
    return w

def response_map_on_ax(ax, resp, boundary, title=None):
    q = resp.dropna(subset=["latitude","longitude","response_t_ha"]).copy()
    if q.empty:
        ax.text(.5,.5,"Not available",transform=ax.transAxes,ha="center",va="center",alpha=.55)
        ax.set_axis_off()
        return None

    districts = set(q["district"].dropna())
    draw_boundary_and_labels(ax, boundary, districts)
    xlim, ylim = global_limits(boundary, districts)

    vmax = max(abs(float(q["response_t_ha"].min())), abs(float(q["response_t_ha"].max())), .1)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    sc = ax.scatter(
        q["longitude"], q["latitude"],
        c=q["response_t_ha"], cmap=DIFF_CMAP, norm=norm,
        s=58, edgecolors="black", linewidths=.25, zorder=5
    )
    for _, r in q.iterrows():
        ax.annotate(
            f"{r['response_t_ha']:.1f}",
            (r["longitude"],r["latitude"]),
            xytext=(4,4), textcoords="offset points",
            fontsize=7.0, fontweight="semibold", zorder=9
        )

    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    if title:
        ax.set_title(title, fontsize=10.5, fontweight="semibold")
    return sc

def paired_stage_page(
    year, treatment_role, comparator_role,
    treatment_label, comparator_label,
    title, outfile, dataset_type="Trial"
):
    df = load_data()
    q = df.loc[
        df["year"].eq(year)
        & df["dataset_type"].astype(str).str.lower().eq(dataset_type.lower())
        & df["treatment_role"].isin([treatment_role, comparator_role])
    ].copy()

    boundary = load_boundary()
    s = site_means(q)
    resp = response_df(q, treatment_role, comparator_role)

    fig = plt.figure(figsize=(15, 8.8))
    gs = GridSpec(2, 3, figure=fig, height_ratios=[1.0, 1.35], hspace=.30, wspace=.18)

    ax1 = fig.add_subplot(gs[0,0])
    violin_on_ax(
        ax1,
        q.loc[q["treatment_role"].eq(comparator_role),"yield_t_ha"],
        ROLE_COLORS.get(comparator_role,"#777777"),
        comparator_label
    )
    ax1.set_ylabel("Maize grain yield (t ha$^{-1}$)")
    ax1.set_title("Comparator distribution", fontsize=11)

    ax2 = fig.add_subplot(gs[0,1])
    violin_on_ax(
        ax2,
        q.loc[q["treatment_role"].eq(treatment_role),"yield_t_ha"],
        ROLE_COLORS.get(treatment_role,"#4C78A8"),
        treatment_label
    )
    ax2.set_title("Treatment distribution", fontsize=11)

    ax3 = fig.add_subplot(gs[0,2])
    violin_on_ax(
        ax3,
        resp["response_t_ha"] if not resp.empty else [],
        "#555555",
        "Treatment − comparator"
    )
    ax3.axhline(0, color="black", linestyle="--", linewidth=.8)
    ax3.set_ylabel("Yield response (t ha$^{-1}$)")
    ax3.set_title("Site-level response", fontsize=11)

    c = s.loc[s["treatment_role"].eq(comparator_role)]
    t = s.loc[s["treatment_role"].eq(treatment_role)]
    allvals = pd.concat([c["mean_yield_t_ha"],t["mean_yield_t_ha"]]).dropna()
    vmin = float(allvals.min()) if len(allvals) else 0
    vmax = float(allvals.max()) if len(allvals) else 1

    ax4 = fig.add_subplot(gs[1,0])
    sc1 = yield_map_on_ax(ax4,c,boundary,comparator_label,vmin,vmax)

    ax5 = fig.add_subplot(gs[1,1])
    sc2 = yield_map_on_ax(ax5,t,boundary,treatment_label,vmin,vmax)

    ax6 = fig.add_subplot(gs[1,2])
    sc3 = response_map_on_ax(ax6,resp,boundary,"Yield response")

    for ax in [ax4,ax5,ax6]:
        if ax.axison:
            ax.set_xlabel("Longitude (degrees)")
            ax.set_ylabel("Latitude (degrees)")

    if sc2 is not None:
        cax = fig.add_axes([.14,.055,.40,.020])
        cb = fig.colorbar(sc2,cax=cax,orientation="horizontal")
        cb.set_label("Maize grain yield (t ha$^{-1}$)")

    if sc3 is not None:
        cax2 = fig.add_axes([.64,.055,.22,.020])
        cb2 = fig.colorbar(sc3,cax=cax2,orientation="horizontal")
        cb2.set_label("Yield response (t ha$^{-1}$)")

    fig.suptitle(title, fontsize=15, fontweight="semibold", y=.98)
    fig.subplots_adjust(bottom=.12, top=.92)
    fig.savefig(FIGURES/outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def soil_background_page(outfile="01a_soil_background_all_years.png"):
    df = trial_only(load_data())
    q = df.loc[df["treatment_role"].eq("soil_background")].copy()
    boundary = load_boundary()
    s = site_means(q)
    years=[2017,2018,2019]

    allvals=s["mean_yield_t_ha"].dropna()
    vmin=float(allvals.min()); vmax=float(allvals.max())

    fig=plt.figure(figsize=(16,9))
    gs=GridSpec(2,3,figure=fig,height_ratios=[.72,1.45],hspace=.28,wspace=.16)

    last=None
    for j,year in enumerate(years):
        qq=q.loc[q["year"].eq(year)]
        axv=fig.add_subplot(gs[0,j])
        violin_on_ax(axv,qq["yield_t_ha"],ROLE_COLORS["soil_background"],str(year))
        if j==0:
            axv.set_ylabel("Maize grain yield (t ha$^{-1}$)")
        axv.set_title(f"{year}: N0-P0-K0",fontsize=11,fontweight="semibold")

        axm=fig.add_subplot(gs[1,j])
        ss=s.loc[s["year"].eq(year)]
        last=yield_map_on_ax(axm,ss,boundary,f"{year}: N0-P0-K0",vmin,vmax)
        axm.set_xlabel("Longitude (degrees)")
        if j==0:
            axm.set_ylabel("Latitude (degrees)")

    if last is not None:
        cax=fig.add_axes([.30,.055,.40,.022])
        cb=fig.colorbar(last,cax=cax,orientation="horizontal")
        cb.set_label("Maize grain yield (t ha$^{-1}$)")

    fig.suptitle("Soil background yield across NSAF maize trials",fontsize=15,fontweight="semibold",y=.98)
    fig.subplots_adjust(bottom=.13,top=.92)
    fig.savefig(FIGURES/outfile,dpi=300,bbox_inches="tight")
    plt.close(fig)

def omission_matrix_page(outfile="01_omission_diagnostics_year_by_nutrient.png"):
    df=trial_only(load_data())
    boundary=load_boundary()

    specs=[
        ("n_omission","N-limited yield"),
        ("p_omission","P-limited yield"),
        ("k_omission","K-limited yield"),
    ]
    years=[2017,2018,2019]
    q=df.loc[df["treatment_role"].isin([x[0] for x in specs])].copy()
    s=site_means(q)

    allvals=s["mean_yield_t_ha"].dropna()
    vmin=float(allvals.min()) if len(allvals) else 0
    vmax=float(allvals.max()) if len(allvals) else 1

    fig=plt.figure(figsize=(18,15))
    outer=GridSpec(3,3,figure=fig,hspace=.24,wspace=.13)

    last=None
    for i,year in enumerate(years):
        for j,(role,label) in enumerate(specs):
            inner=GridSpecFromSubplotSpec(
                2,1,subplot_spec=outer[i,j],
                height_ratios=[.45,1.35],hspace=.08
            )

            axv=fig.add_subplot(inner[0,0])
            vals=q.loc[q["year"].eq(year)&q["treatment_role"].eq(role),"yield_t_ha"]
            violin_on_ax(axv,vals,ROLE_COLORS.get(role,"#4C78A8"),"")
            axv.set_xticks([])
            if j==0:
                axv.set_ylabel(f"{year}\nYield")
            if i==0:
                axv.set_title(label,fontsize=12,fontweight="semibold")

            axm=fig.add_subplot(inner[1,0])
            ss=s.loc[s["year"].eq(year)&s["treatment_role"].eq(role)]
            last=yield_map_on_ax(axm,ss,boundary,None,vmin,vmax)
            axm.set_xlabel("Longitude")
            if j==0:
                axm.set_ylabel("Latitude")

    if last is not None:
        cax=fig.add_axes([.30,.035,.40,.018])
        cb=fig.colorbar(last,cax=cax,orientation="horizontal")
        cb.set_label("Mean maize grain yield (t ha$^{-1}$)")

    fig.suptitle(
        "N-, P- and K-limited maize yield by year",
        fontsize=16,fontweight="semibold",y=.995
    )
    fig.subplots_adjust(bottom=.08,top=.965)
    fig.savefig(FIGURES/outfile,dpi=300,bbox_inches="tight")
    plt.close(fig)
