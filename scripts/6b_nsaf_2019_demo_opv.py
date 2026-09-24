from nsaf_post1_common import *
roles=[
    "demo_gr_opv","demo_fym_opv","demo_zn_opv",
    "demo_pcu_half_n_opv","demo_udp_reduced_n_opv"
]
labels={
    "demo_gr_opv":"B1 N120-P60-K40",
    "demo_fym_opv":"B2 FYM + full NPK",
    "demo_zn_opv":"B3 Zn + full NPK",
    "demo_pcu_half_n_opv":"B4 PCU N60",
    "demo_udp_reduced_n_opv":"B5 UDP N78",
}
strategy_stage(
    "6b_2019_demo_opv",2019,"OPV",roles,labels,
    "demo_gr_opv","2019 Demo: OPV"
)
