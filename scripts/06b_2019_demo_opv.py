from nsaf_stage_common import *
roles=[
    "demo_gr_opv","demo_fym_opv","demo_zn_opv",
    "demo_pcu_half_n_opv","demo_udp_reduced_n_opv"
]
labels={
    "demo_gr_opv":"B1 OPV N120-P60-K40",
    "demo_fym_opv":"B2 OPV FYM + N120-P60-K40",
    "demo_zn_opv":"B3 OPV Zn + N120-P60-K40",
    "demo_pcu_half_n_opv":"B4 OPV PCU N60-P60-K40",
    "demo_udp_reduced_n_opv":"B5 OPV UDP N78-P60-K40",
}
run_multi_stage("06b_2019_demo_opv",2019,"Demo",roles,labels,"2019 Demo — OPV")
for role in roles[1:]:
    run_pair_stage(
        "06b_"+role,2019,"Demo",role,"demo_gr_opv",
        labels[role],labels["demo_gr_opv"],
        "2019 Demo — OPV: "+labels[role]
    )
