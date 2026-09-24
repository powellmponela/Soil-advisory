from nsaf_stage_common import *
df=load_data()
q=select(df,2018,"Demo")
roles=list(q["treatment_role"].dropna().unique())
labels={r:r.replace("demo_","").upper() for r in roles}
run_multi_stage(
    "04a_2018_demo",2018,"Demo",
    roles,labels,"2018 maize demonstration"
)
