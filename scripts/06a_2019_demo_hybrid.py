from nsaf_stage_common import *
roles=[
    "demo_gr_hybrid","demo_fym_hybrid","demo_zn_hybrid",
    "demo_pcu_half_n_hybrid","demo_udp_reduced_n_hybrid"
]
labels={
    "demo_gr_hybrid":"A1 Hybrid N120-P60-K40",
    "demo_fym_hybrid":"A2 Hybrid FYM + N120-P60-K40",
    "demo_zn_hybrid":"A3 Hybrid Zn + N120-P60-K40",
    "demo_pcu_half_n_hybrid":"A4 Hybrid PCU N60-P60-K40",
    "demo_udp_reduced_n_hybrid":"A5 Hybrid UDP N78-P60-K40",
}
run_multi_stage("06a_2019_demo_hybrid",2019,"Demo",roles,labels,"2019 Demo — Hybrid")
for role in roles[1:]:
    run_pair_stage(
        "06a_"+role,2019,"Demo",role,"demo_gr_hybrid",
        labels[role],labels["demo_gr_hybrid"],
        "2019 Demo — Hybrid: "+labels[role]
    )
