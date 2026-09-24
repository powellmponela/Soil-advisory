from nsaf_stage1_common import *

df = trial_only(load_data())
boundary = load_boundary()

roles = [
    "soil_background",
    "k_omission",
]

labels = {
    "soil_background":
        "Unfertilized control (0–0–0)",
    "k_omission":
        "K omission (−K): N120–P60–K0",
}

fixed_districts = sorted(
    set(
        df.loc[
            df["treatment_role"].isin(roles),
            "district",
        ]
        .dropna()
        .astype(str)
    )
)

fig = plt.figure(figsize=(16, 9))

gs = GridSpec(
    2, 3,
    figure=fig,
    height_ratios=[0.78, 1.38],
    hspace=0.30,
    wspace=0.16,
)

last = None
all_resp = []

for j, year in enumerate(YEARS):
    q = df.loc[
        df["year"].eq(year)
        & df["treatment_role"].isin(roles)
    ].copy()

    axv = fig.add_subplot(gs[0, j])

    violin_grouped(
        axv,
        q,
        roles,
        labels,
    )

    axv.set_title(
        str(year),
        fontsize=12,
        fontweight="semibold",
    )

    if j == 0:
        axv.set_ylabel(
            "Maize grain yield "
            "(t ha$^{-1}$)"
        )

    # 2018 has no K-omission treatment.
    if (
        year == 2018
        and not q[
            "treatment_role"
        ].eq(
            "k_omission"
        ).any()
    ):
        resp = pd.DataFrame()

    else:
        resp = paired_site_response(
            q,
            "k_omission",
            "soil_background",
        )

        if not resp.empty:
            resp["year"] = year
            all_resp.append(resp)

    axm = fig.add_subplot(gs[1, j])

    last_here = response_map_on_ax(
        axm,
        resp,
        boundary,
        fixed_districts=fixed_districts,
        title=(
            f"{year}: "
            "Yield response to N+P"
        ),
    )

    if last_here is not None:
        last = last_here

    axm.set_xlabel(
        "Longitude (degrees)"
    )

    if j == 0:
        axm.set_ylabel(
            "Latitude (degrees)"
        )

if last is not None:
    cax = fig.add_axes(
        [0.30, 0.055, 0.40, 0.022]
    )

    cb = fig.colorbar(
        last,
        cax=cax,
        orientation="horizontal",
    )

    cb.set_label(
        "Yield response to N+P "
        "(t ha$^{-1}$)"
    )

fig.suptitle(
    "Yield response to N+P: "
    "K omission compared with "
    "the unfertilized control",
    fontsize=15,
    fontweight="semibold",
    y=0.98,
)

fig.subplots_adjust(
    bottom=0.13,
    top=0.92,
)

save(
    fig,
    "1d_nsaf_k_omission_vs_zero_explore.png",
)

if all_resp:
    pd.concat(
        all_resp,
        ignore_index=True,
    ).to_csv(
        TABLES
        / (
            "1d_nsaf_k_omission_vs_zero_"
            "explore_site_response.csv"
        ),
        index=False,
    )

print(
    "2018 K omission unavailable; "
    "2017 and 2019 processed normally."
)
