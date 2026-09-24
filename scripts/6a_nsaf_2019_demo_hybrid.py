from nsaf_post1_common import *
roles=[
    "demo_gr_hybrid","demo_fym_hybrid","demo_zn_hybrid",
    "demo_pcu_half_n_hybrid","demo_udp_reduced_n_hybrid"
]
labels={
    "demo_gr_hybrid":"A1 N120-P60-K40",
    "demo_fym_hybrid":"A2 FYM + full NPK",
    "demo_zn_hybrid":"A3 Zn + full NPK",
    "demo_pcu_half_n_hybrid":"A4 PCU N60",
    "demo_udp_reduced_n_hybrid":"A5 UDP N78",
}
strategy_stage(
    "6a_2019_demo_hybrid",2019,"Hybrid",roles,labels,
    "demo_gr_hybrid","2019 Demo: Hybrid"
)
