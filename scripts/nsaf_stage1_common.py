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

for folder in [FIGURES, MAPS, TABLES]:
    folder.mkdir(parents=True, exist_ok=True)

YEARS = [2017, 2018, 2019]

DISTRICT_ALIASES = {
    "doti":"Doti",
    "surkhet":"Surkhet",
    "salyan":"Salyan",
    "dang":"Dang",
    "palpa":"Palpa",
    "makwanpur":"Makwanpur",
    "makawanpur":"Makwanpur",
    "nuwakot":"Nuwakot",
    "kavre":"Kavre",
    "kavrepalanchok":"Kavre",
    "kavrepalanchowk":"Kavre",
    "kabhrepalanchok":"Kavre",
    "kabhrepalanchowk":"Kavre",
    "chitwan":"Chitwan",
}

ROLE_COLORS = {
    "soil_background":"#7F7F7F",
    "n_omission":"#009E73",
    "p_omission":"#E69F00",
    "k_omission":"#CC79A7",
    "government_recommendation":"#0072B2",
}

RESPONSE_CMAP = LinearSegmentedColormap.from_list(
    "response_red_yellow_green",
    ["#B2182B","#F4A582","#FFF3A1","#A6D96A","#1A9850"]
)

AE_CMAPS = {
    "N":"YlGnBu",
    "P":"YlOrBr",
    "K":"PuRd",
}

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
        "treatment","N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha",
        "yield_14pct_kg_ha",
    }

    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            "Run 0a_nsaf_maize_ingest.py first; missing: "
            + ", ".join(missing)
        )

    for c in [
        "year","latitude","longitude",
        "N_rate_kg_ha","P_rate_kg_ha","K_rate_kg_ha",
        "yield_14pct_kg_ha",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["district"] = df["district"].map(norm_district)
    df["yield_t_ha"] = df["yield_14pct_kg_ha"] / 1000.0

    return df

def trial_only(df):
    return df.loc[
        df["dataset_type"]
        .astype(str)
        .str.lower()
        .eq("trial")
    ].copy()

def load_boundary():
    b = gpd.read_file(BOUNDARY)

    if b.crs is None:
        raise ValueError("Boundary CRS is missing.")

    b = b.to_crs(epsg=4326)

    dcol = next(
        (
            c for c in [
                "district","District","DISTRICT",
                "dist_name","DIST_NAME","NAME_2"
            ]
            if c in b.columns
        ),
        None,
    )

    if dcol is None:
        raise ValueError(
            "District field not found in boundary."
        )

    b["_district"] = b[dcol].map(norm_district)
    return b

def site_means(q):
    return (
        q.groupby(
            [
                "year","study","dataset_type",
                "district","site","treatment_role",
            ],
            dropna=False,
        )
        .agg(
            mean_yield_t_ha=("yield_t_ha","mean"),
            latitude=("latitude","mean"),
            longitude=("longitude","mean"),
            n=("yield_t_ha","count"),
        )
        .reset_index()
    )

def paired_site_response(
    q,
    treatment_role,
    comparator_role,
    response_name="response_t_ha",
):
    s = site_means(
        q.loc[
            q["treatment_role"]
            .isin([treatment_role, comparator_role])
        ]
    )

    if s.empty:
        return pd.DataFrame()

    w = (
        s.pivot_table(
            index=[
                "year","study","dataset_type",
                "district","site",
            ],
            columns="treatment_role",
            values="mean_yield_t_ha",
            aggfunc="first",
        )
        .reset_index()
    )

    if (
        treatment_role not in w.columns
        or comparator_role not in w.columns
    ):
        return pd.DataFrame()

    coords = (
        s.groupby(
            [
                "year","study","dataset_type",
                "district","site",
            ],
            dropna=False,
        )
        .agg(
            latitude=("latitude","mean"),
            longitude=("longitude","mean"),
        )
        .reset_index()
    )

    w = w.merge(
        coords,
        on=[
            "year","study","dataset_type",
            "district","site",
        ],
        how="left",
    )

    w[response_name] = (
        w[treatment_role]
        - w[comparator_role]
    )

    return w

def district_label_df(
    boundary,
    districts,
):
    d = (
        boundary.loc[
            boundary["_district"].isin(districts),
            ["_district","geometry"],
        ]
        .dissolve(by="_district")
        .reset_index()
    )

    if d.empty:
        return pd.DataFrame(
            columns=[
                "district","x","y","dx","dy"
            ]
        )

    rp = d.geometry.representative_point()

    lab = pd.DataFrame({
        "district":d["_district"].values,
        "x":rp.x.values,
        "y":rp.y.values,
    })

    offsets = {
        "Doti":(-24,14),
        "Surkhet":(-24,-18),
        "Salyan":(-10,16),
        "Dang":(-18,-18),
        "Palpa":(8,-18),
        "Makwanpur":(12,-18),
        "Nuwakot":(12,16),
        "Kavre":(16,-14),
        "Chitwan":(12,-18),
    }

    lab["dx"] = lab["district"].map(
        lambda x: offsets.get(x,(8,8))[0]
    )
    lab["dy"] = lab["district"].map(
        lambda x: offsets.get(x,(8,8))[1]
    )

    return lab

def draw_boundary_callouts(
    ax,
    boundary,
    districts,
):
    districts = list(districts)

    bb = boundary.loc[
        boundary["_district"].isin(districts)
    ].copy()

    if bb.empty:
        return

    bb.boundary.plot(
        ax=ax,
        color="0.82",
        linewidth=0.35,
        zorder=1,
    )

    (
        bb[["_district","geometry"]]
        .dissolve(by="_district")
        .boundary.plot(
            ax=ax,
            color="0.35",
            linewidth=0.9,
            zorder=2,
        )
    )

    labels = district_label_df(
        boundary,
        districts,
    )

    for _, r in labels.iterrows():
        ax.annotate(
            r["district"],
            xy=(r["x"], r["y"]),
            xytext=(r["dx"], r["dy"]),
            textcoords="offset points",
            fontsize=8.2,
            ha="center",
            va="center",
            arrowprops=dict(
                arrowstyle="-",
                linewidth=0.55,
                color="0.35",
            ),
            bbox=dict(
                facecolor="white",
                edgecolor="none",
                alpha=0.72,
                pad=0.7,
            ),
            zorder=8,
        )

def map_limits(
    boundary,
    districts,
):
    districts = list(districts)

    bb = boundary.loc[
        boundary["_district"].isin(districts)
    ].copy()

    if bb.empty:
        return (
            (80.0,86.5),
            (26.5,30.0),
        )

    minx,miny,maxx,maxy = bb.total_bounds

    dx = max(
        maxx-minx,
        0.1,
    )
    dy = max(
        maxy-miny,
        0.1,
    )

    return (
        (minx-0.05*dx,maxx+0.05*dx),
        (miny-0.08*dy,maxy+0.08*dy),
    )

def violin_grouped(
    ax,
    q,
    roles,
    labels,
):
    data = []
    positions = []
    roles_found = []
    xt = []

    for i, role in enumerate(
        roles,
        start=1,
    ):
        vals = (
            q.loc[
                q["treatment_role"].eq(role),
                "yield_t_ha",
            ]
            .dropna()
            .to_numpy()
        )

        if len(vals):
            data.append(vals)
            positions.append(i)
            roles_found.append(role)
            xt.append(
                labels.get(role,role)
            )

    if not data:
        ax.text(
            0.5,0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            alpha=0.55,
        )
        return

    parts = ax.violinplot(
        data,
        positions=positions,
        widths=0.72,
        showmeans=False,
        showmedians=True,
        showextrema=False,
    )

    for body,role in zip(
        parts["bodies"],
        roles_found,
    ):
        col = ROLE_COLORS.get(
            role,
            "#4C78A8",
        )

        body.set_facecolor(col)
        body.set_edgecolor(col)
        body.set_alpha(0.22)
        body.set_linewidth(1.0)

    parts["cmedians"].set_color(
        "black"
    )
    parts["cmedians"].set_linewidth(
        1.2
    )

    rng = np.random.default_rng(42)

    for x,vals,role in zip(
        positions,
        data,
        roles_found,
    ):
        ax.scatter(
            np.full(len(vals),x)
            + rng.uniform(
                -0.10,
                0.10,
                len(vals),
            ),
            vals,
            s=19,
            color=ROLE_COLORS.get(
                role,
                "#4C78A8",
            ),
            alpha=0.80,
            edgecolors="none",
            zorder=5,
        )

    ax.set_xticks(
        positions
    )
    ax.set_xticklabels(
        xt,
        rotation=28,
        ha="right",
        fontsize=9.5,
    )
    ax.grid(
        axis="y",
        alpha=0.18,
    )

def violin_single(
    ax,
    values,
    label="",
    color="#555555",
    ylabel=None,
):
    vals = (
        pd.Series(values)
        .dropna()
        .to_numpy()
    )

    if len(vals) == 0:
        ax.text(
            0.5,0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            alpha=0.55,
        )
        ax.set_xticks([])
        return

    parts = ax.violinplot(
        [vals],
        positions=[1],
        widths=0.72,
        showmeans=False,
        showmedians=True,
        showextrema=False,
    )

    body = parts["bodies"][0]
    body.set_facecolor(color)
    body.set_edgecolor(color)
    body.set_alpha(0.22)

    parts["cmedians"].set_color(
        "black"
    )
    parts["cmedians"].set_linewidth(
        1.2
    )

    rng = np.random.default_rng(42)

    ax.scatter(
        np.ones(len(vals))
        + rng.uniform(
            -0.10,
            0.10,
            len(vals),
        ),
        vals,
        s=19,
        color=color,
        alpha=0.80,
        edgecolors="none",
        zorder=5,
    )

    ax.set_xticks([1])
    ax.set_xticklabels(
        [label],
        fontsize=9.5,
    )

    if ylabel:
        ax.set_ylabel(ylabel)

    ax.grid(
        axis="y",
        alpha=0.18,
    )

def yield_map_on_ax(
    ax,
    s,
    boundary,
    fixed_districts=None,
    title=None,
    vmin=None,
    vmax=None,
    cmap="YlGnBu",
):
    required = {
        "latitude",
        "longitude",
        "mean_yield_t_ha",
    }

    if (
        s is None
        or not isinstance(s,pd.DataFrame)
        or s.empty
        or not required.issubset(s.columns)
    ):
        ax.text(
            0.5,0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            alpha=0.55,
        )

        if fixed_districts:
            draw_boundary_callouts(
                ax,
                boundary,
                fixed_districts,
            )
            xlim,ylim = map_limits(
                boundary,
                fixed_districts,
            )
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect(
                "equal",
                adjustable="box",
            )

        if title:
            ax.set_title(
                title,
                fontsize=10.5,
                fontweight="semibold",
            )

        return None

    s = s.dropna(
        subset=[
            "latitude",
            "longitude",
            "mean_yield_t_ha",
        ]
    ).copy()

    if s.empty:
        return None

    districts = (
        fixed_districts
        if fixed_districts
        else set(
            s["district"].dropna()
        )
    )

    draw_boundary_callouts(
        ax,
        boundary,
        districts,
    )

    xlim,ylim = map_limits(
        boundary,
        districts,
    )

    if vmin is None:
        vmin = float(
            s["mean_yield_t_ha"].min()
        )

    if vmax is None:
        vmax = float(
            s["mean_yield_t_ha"].max()
        )

    if vmin == vmax:
        vmax = vmin + 1

    sc = ax.scatter(
        s["longitude"],
        s["latitude"],
        c=s["mean_yield_t_ha"],
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        s=58,
        edgecolors="black",
        linewidths=0.25,
        zorder=5,
    )

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(
        "equal",
        adjustable="box",
    )
    ax.grid(False)

    if title:
        ax.set_title(
            title,
            fontsize=10.5,
            fontweight="semibold",
        )

    return sc

def response_map_on_ax(
    ax,
    resp,
    boundary,
    fixed_districts=None,
    response_col="response_t_ha",
    title=None,
):
    """
    Plot a site-level response map.

    Missing contrasts are shown explicitly as 'Not available'.
    This is required for 2018 K omission, which is absent by design
    in the current harmonised trial dataset.
    """

    required = {
        "latitude",
        "longitude",
        response_col,
    }

    if (
        resp is None
        or not isinstance(resp,pd.DataFrame)
        or resp.empty
        or not required.issubset(resp.columns)
    ):
        ax.text(
            0.5,
            0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            alpha=0.60,
        )

        if fixed_districts:
            draw_boundary_callouts(
                ax,
                boundary,
                fixed_districts,
            )

            xlim,ylim = map_limits(
                boundary,
                fixed_districts,
            )

            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect(
                "equal",
                adjustable="box",
            )

        if title:
            ax.set_title(
                title,
                fontsize=10.5,
                fontweight="semibold",
            )

        ax.grid(False)
        return None

    q = resp.dropna(
        subset=[
            "latitude",
            "longitude",
            response_col,
        ]
    ).copy()

    if q.empty:
        ax.text(
            0.5,
            0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            alpha=0.60,
        )

        if fixed_districts:
            draw_boundary_callouts(
                ax,
                boundary,
                fixed_districts,
            )

            xlim,ylim = map_limits(
                boundary,
                fixed_districts,
            )

            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect(
                "equal",
                adjustable="box",
            )

        if title:
            ax.set_title(
                title,
                fontsize=10.5,
                fontweight="semibold",
            )

        ax.grid(False)
        return None

    districts = (
        fixed_districts
        if fixed_districts
        else set(
            q["district"].dropna()
        )
    )

    draw_boundary_callouts(
        ax,
        boundary,
        districts,
    )

    xlim,ylim = map_limits(
        boundary,
        districts,
    )

    vmax = max(
        abs(
            float(
                q[response_col].min()
            )
        ),
        abs(
            float(
                q[response_col].max()
            )
        ),
        0.1,
    )

    norm = TwoSlopeNorm(
        vmin=-vmax,
        vcenter=0,
        vmax=vmax,
    )

    sc = ax.scatter(
        q["longitude"],
        q["latitude"],
        c=q[response_col],
        cmap=RESPONSE_CMAP,
        norm=norm,
        s=60,
        edgecolors="black",
        linewidths=0.25,
        zorder=5,
    )

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(
        "equal",
        adjustable="box",
    )
    ax.grid(False)

    if title:
        ax.set_title(
            title,
            fontsize=10.5,
            fontweight="semibold",
        )

    return sc

def ae_map_on_ax(
    ax,
    ae,
    nutrient,
    boundary,
    fixed_districts=None,
    title=None,
):
    col = f"AE_{nutrient}_kg_kg"

    required = {
        "latitude",
        "longitude",
        col,
    }

    if (
        ae is None
        or not isinstance(ae,pd.DataFrame)
        or ae.empty
        or not required.issubset(ae.columns)
    ):
        ax.text(
            0.5,
            0.5,
            "Not available",
            transform=ax.transAxes,
            ha="center",
            va="center",
            alpha=0.55,
        )

        if fixed_districts:
            draw_boundary_callouts(
                ax,
                boundary,
                fixed_districts,
            )

            xlim,ylim = map_limits(
                boundary,
                fixed_districts,
            )
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect(
                "equal",
                adjustable="box",
            )

        return None

    q = ae.dropna(
        subset=[
            "latitude",
            "longitude",
            col,
        ]
    ).copy()

    if q.empty:
        return None

    districts = (
        fixed_districts
        if fixed_districts
        else set(
            q["district"].dropna()
        )
    )

    draw_boundary_callouts(
        ax,
        boundary,
        districts,
    )

    xlim,ylim = map_limits(
        boundary,
        districts,
    )

    vmin = float(
        q[col].min()
    )
    vmax = float(
        q[col].max()
    )

    if vmin == vmax:
        vmax = vmin + 1

    sc = ax.scatter(
        q["longitude"],
        q["latitude"],
        c=q[col],
        cmap=AE_CMAPS[nutrient],
        vmin=vmin,
        vmax=vmax,
        s=60,
        edgecolors="black",
        linewidths=0.25,
        zorder=5,
    )

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(
        "equal",
        adjustable="box",
    )
    ax.grid(False)

    if title:
        ax.set_title(
            title,
            fontsize=10.5,
            fontweight="semibold",
        )

    return sc

def save(
    fig,
    filename,
):
    fig.savefig(
        FIGURES / filename,
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig)
