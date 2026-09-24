from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

ROOT = Path(r"D:\dss\SOIL ADVISORY")
DATA = ROOT / "Data" / "NSAF Crops Trial Data" / "Maize" / "harmonised" / "nsaf_maize_key_variables.csv"
BOUNDARY = ROOT / "Data" / "boundary" / "ward_level_boundary.gpkg"

FIGURES = ROOT / "outputs" / "figures"
MAPS = ROOT / "outputs" / "maps"
TABLES = ROOT / "outputs" / "tables"
for p in [FIGURES, MAPS, TABLES]:
    p.mkdir(parents=True, exist_ok=True)

DISTRICT_ALIASES = {
    "doti":"Doti","surkhet":"Surkhet","salyan":"Salyan","dang":"Dang",
    "palpa":"Palpa","makwanpur":"Makwanpur","makawanpur":"Makwanpur",
    "nuwakot":"Nuwakot","kavre":"Kavre","kavrepalanchok":"Kavre",
    "kavrepalanchowk":"Kavre","kabhrepalanchok":"Kavre",
    "kabhrepalanchowk":"Kavre","chitwan":"Chitwan"
}

DISTRICT_ORDER = [
    "Doti","Surkhet","Salyan","Dang","Palpa",
    "Makwanpur","Nuwakot","Kavre","Chitwan"
]

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
    "ks_treatment":"#8C564B",
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
    "negative_yellow_positive",
    ["#B2182B", "#F4A582", "#FFF3A1", "#A6D96A", "#1A9850"]
)

def norm_district(x):
    if pd.isna(x):
        return np.nan
    key = re.sub(r"[^a-z0-9]+", "", str(x).lower())
    return DISTRICT_ALIASES.get(key, str(x).strip())

def load_data():
    df = pd.read_csv(DATA)
    required = {
        "year","study","dataset_type","district","site",
        "latitude","longitude","treatment_code","treatment_role",
        "treatment","yield_14pct_kg_ha"
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
        raise ValueError("Boundary CRS is missing")
    b = b.to_crs(4326)
    dcol = next((c for c in ["district","District","DISTRICT","dist_name","DIST_NAME","NAME_2"] if c in b.columns), None)
    if dcol is None:
        raise ValueError("District field not found in boundary")
    b["_district"] = b[dcol].map(norm_district)
    return b

def select(df, year, dataset_type=None, roles=None, study_contains=None):
    q = df.loc[df["year"].eq(year)].copy()
    if dataset_type is not None:
        q = q.loc[q["dataset_type"].astype(str).str.lower().eq(dataset_type.lower())]
    if roles is not None:
        q = q.loc[q["treatment_role"].isin(roles)]
    if study_contains is not None:
        q = q.loc[q["study"].astype(str).str.contains(study_contains, case=False, na=False)]
    return q.copy()

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

def plot_violin_scatter(q, roles, labels, outfile, title=None):
    data, labs, role_list = [], [], []
    for role in roles:
        vals = q.loc[q["treatment_role"].eq(role), "yield_t_ha"].dropna().to_numpy()
        if len(vals):
            data.append(vals)
            labs.append(labels.get(role, role))
            role_list.append(role)

    if not data:
        print(f"No data for {outfile.name}; graph skipped.")
        return

    fig, ax = plt.subplots(figsize=(max(7.0, 1.65 * len(data) + 3), 6.6))
    pos = np.arange(1, len(data) + 1)
    parts = ax.violinplot(
        data, positions=pos, widths=0.75,
        showmeans=False, showmedians=True, showextrema=False
    )

    for body, role in zip(parts["bodies"], role_list):
        col = ROLE_COLORS.get(role, "#4C78A8")
        body.set_facecolor(col)
        body.set_edgecolor(col)
        body.set_alpha(0.22)
        body.set_linewidth(1.1)

    parts["cmedians"].set_color("black")
    parts["cmedians"].set_linewidth(1.3)

    rng = np.random.default_rng(42)
    for x, vals, role in zip(pos, data, role_list):
        col = ROLE_COLORS.get(role, "#4C78A8")
        jitter = rng.uniform(-0.11, 0.11, len(vals))
        ax.scatter(
            np.full(len(vals), x) + jitter, vals,
            s=22, color=col, alpha=0.80, edgecolors="none", zorder=5
        )

    ax.set_xticks(pos)
    ax.set_xticklabels(labs, rotation=30, ha="right", fontsize=11)
    ax.set_ylabel("Maize grain yield (t ha$^{-1}$)", fontsize=12)
    if title:
        ax.set_title(title, fontsize=13, fontweight="semibold")
    ax.grid(axis="y", alpha=0.20)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def paired_response(q, treatment_role, comparator_role):
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

def plot_response_violin(resp, outfile, title=None):
    vals = resp["response_t_ha"].dropna().to_numpy()
    if len(vals) == 0:
        print(f"No paired response for {outfile.name}; graph skipped.")
        return

    fig, ax = plt.subplots(figsize=(6.8, 6.3))
    parts = ax.violinplot(
        [vals], positions=[1], widths=0.75,
        showmeans=False, showmedians=True, showextrema=False
    )
    body = parts["bodies"][0]
    body.set_facecolor("#777777")
    body.set_edgecolor("#444444")
    body.set_alpha(0.22)
    parts["cmedians"].set_color("black")
    parts["cmedians"].set_linewidth(1.3)

    rng = np.random.default_rng(42)
    ax.scatter(
        np.ones(len(vals)) + rng.uniform(-0.10, 0.10, len(vals)),
        vals, s=24, alpha=0.78, color="#444444", edgecolors="none", zorder=5
    )
    ax.axhline(0, color="black", linewidth=0.9, linestyle="--")
    ax.set_xticks([1])
    ax.set_xticklabels(["Treatment − comparator"])
    ax.set_ylabel("Yield response (t ha$^{-1}$)")
    if title:
        ax.set_title(title, fontsize=13, fontweight="semibold")
    ax.grid(axis="y", alpha=0.20)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def district_label_positions(boundary, districts):
    d = (
        boundary.loc[boundary["_district"].isin(districts), ["_district","geometry"]]
        .dissolve(by="_district")
        .reset_index()
    )
    if d.empty:
        return pd.DataFrame(columns=["district","x","y"])
    pts = d.geometry.representative_point()
    return pd.DataFrame({"district":d["_district"], "x":pts.x, "y":pts.y})

def _base_map(ax, boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    if bb.empty:
        return
    bb.boundary.plot(ax=ax, color="0.82", linewidth=0.35, zorder=1)
    (
        bb[["_district","geometry"]]
        .dissolve(by="_district")
        .boundary.plot(ax=ax, color="0.35", linewidth=0.9, zorder=2)
    )
    labels = district_label_positions(boundary, districts)
    for _, r in labels.iterrows():
        ax.text(r["x"], r["y"], r["district"], ha="center", va="center", fontsize=8.0, zorder=6)

def _limits(boundary, districts):
    bb = boundary.loc[boundary["_district"].isin(districts)].copy()
    minx,miny,maxx,maxy = bb.total_bounds
    dx = max(maxx-minx, 0.1)
    dy = max(maxy-miny, 0.1)
    return (minx-.05*dx,maxx+.05*dx), (miny-.08*dy,maxy+.08*dy)

def plot_yield_map(q, role, label, outfile):
    s = site_means(q.loc[q["treatment_role"].eq(role)]).dropna(
        subset=["latitude","longitude","mean_yield_t_ha"]
    )
    if s.empty:
        print(f"No data for {outfile.name}; map skipped.")
        return

    boundary = load_boundary()
    districts = set(s["district"].dropna())
    xlim, ylim = _limits(boundary, districts)

    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    _base_map(ax, boundary, districts)

    sc = ax.scatter(
        s["longitude"], s["latitude"], c=s["mean_yield_t_ha"],
        cmap="viridis_r", s=62, edgecolors="black", linewidths=0.25, zorder=5
    )
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title(label, fontsize=13, fontweight="semibold")

    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.045, pad=0.10)
    cb.set_label("Maize grain yield (t ha$^{-1}$)")
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_response_map(resp, outfile, title=None):
    q = resp.dropna(subset=["latitude","longitude","response_t_ha"]).copy()
    if q.empty:
        print(f"No paired response for {outfile.name}; map skipped.")
        return

    boundary = load_boundary()
    districts = set(q["district"].dropna())
    xlim, ylim = _limits(boundary, districts)

    vmax = max(abs(float(q["response_t_ha"].min())), abs(float(q["response_t_ha"].max())), 0.1)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    _base_map(ax, boundary, districts)
    sc = ax.scatter(
        q["longitude"], q["latitude"], c=q["response_t_ha"],
        cmap=DIFF_CMAP, norm=norm,
        s=65, edgecolors="black", linewidths=0.25, zorder=5
    )

    for _, r in q.iterrows():
        ax.annotate(
            f"{r['response_t_ha']:.1f}",
            (r["longitude"], r["latitude"]),
            xytext=(5,5), textcoords="offset points",
            fontsize=7.5, fontweight="semibold", zorder=7
        )

    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    if title:
        ax.set_title(title, fontsize=13, fontweight="semibold")

    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.045, pad=0.10)
    cb.set_label("Yield response: treatment − comparator (t ha$^{-1}$)")
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)

def run_pair_stage(
    stage_id, year, dataset_type,
    treatment_role, comparator_role,
    treatment_label, comparator_label,
    stage_title, study_contains=None
):
    df = load_data()
    q = select(
        df, year=year, dataset_type=dataset_type,
        roles=[treatment_role, comparator_role],
        study_contains=study_contains
    )

    labels = {
        comparator_role: comparator_label,
        treatment_role: treatment_label,
    }

    plot_violin_scatter(
        q, [comparator_role, treatment_role], labels,
        FIGURES / f"{stage_id}_yield_violin_scatter.png",
        stage_title
    )

    plot_yield_map(
        q, comparator_role, comparator_label,
        MAPS / f"{stage_id}_comparator_yield_map.png"
    )
    plot_yield_map(
        q, treatment_role, treatment_label,
        MAPS / f"{stage_id}_treatment_yield_map.png"
    )

    resp = paired_response(q, treatment_role, comparator_role)
    resp.to_csv(TABLES / f"{stage_id}_site_response.csv", index=False)

    plot_response_violin(
        resp,
        FIGURES / f"{stage_id}_response_violin_scatter.png",
        stage_title + " — yield response"
    )
    plot_response_map(
        resp,
        MAPS / f"{stage_id}_response_map.png",
        stage_title + " — yield response"
    )

def run_multi_stage(
    stage_id, year, dataset_type,
    roles, labels, stage_title, study_contains=None
):
    df = load_data()
    q = select(
        df, year=year, dataset_type=dataset_type,
        roles=roles, study_contains=study_contains
    )
    plot_violin_scatter(
        q, roles, labels,
        FIGURES / f"{stage_id}_yield_violin_scatter.png",
        stage_title
    )
    for role in roles:
        plot_yield_map(
            q, role, labels.get(role, role),
            MAPS / f"{stage_id}_{role}_yield_map.png"
        )

def run_n_rate_stage():
    df = load_data()
    q = select(
        df, 2017, "Trial",
        roles=["n_omission","n_rate_60","government_recommendation","n_rate_180","n_rate_210"]
    ).copy()

    rate_map = {
        "n_omission":0,
        "n_rate_60":60,
        "government_recommendation":120,
        "n_rate_180":180,
        "n_rate_210":210,
    }
    labels = {r:f"{n} kg N ha$^{{-1}}$" for r,n in rate_map.items()}
    roles = list(rate_map)

    plot_violin_scatter(
        q, roles, labels,
        FIGURES / "02a_2017_n_rate_yield_violin_scatter.png",
        "2017 N-rate response under fixed P60-K40"
    )

    s = site_means(q)
    s["N_rate_kg_ha"] = s["treatment_role"].map(rate_map)
    s.to_csv(TABLES / "02a_2017_n_rate_site_means.csv", index=False)

    # Site response curves
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    for (district, site), g in s.groupby(["district","site"], dropna=False):
        g = g.sort_values("N_rate_kg_ha")
        if g["N_rate_kg_ha"].nunique() >= 2:
            ax.plot(
                g["N_rate_kg_ha"], g["mean_yield_t_ha"],
                marker="o", linewidth=1.0, alpha=0.55
            )
    ax.set_xticks([0,60,120,180,210])
    ax.set_xlabel("N rate (kg N ha$^{-1}$)")
    ax.set_ylabel("Maize grain yield (t ha$^{-1}$)")
    ax.set_title("2017 site-level N-response curves", fontweight="semibold")
    ax.grid(alpha=0.20)
    fig.tight_layout()
    fig.savefig(FIGURES / "02a_2017_n_rate_site_response_curves.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Map best observed tested N rate at each site.
    best = (
        s.sort_values(["district","site","mean_yield_t_ha"])
        .groupby(["year","district","site"], as_index=False)
        .tail(1)
        .copy()
    )
    best.to_csv(TABLES / "02a_2017_best_observed_n_rate_by_site.csv", index=False)

    boundary = load_boundary()
    districts = set(best["district"].dropna())
    xlim, ylim = _limits(boundary, districts)
    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    _base_map(ax, boundary, districts)
    sc = ax.scatter(
        best["longitude"], best["latitude"], c=best["N_rate_kg_ha"],
        cmap="YlGnBu", vmin=0, vmax=210,
        s=68, edgecolors="black", linewidths=0.25, zorder=5
    )
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Longitude (degrees)"); ax.set_ylabel("Latitude (degrees)")
    ax.set_title("2017 N rate with highest observed site yield", fontweight="semibold")
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.045, pad=0.10)
    cb.set_ticks([0,60,120,180,210])
    cb.set_label("N rate (kg N ha$^{-1}$)")
    fig.tight_layout()
    fig.savefig(MAPS / "02a_2017_best_observed_n_rate_map.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
