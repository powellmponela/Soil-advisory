cd "D:\dss\SOIL ADVISORY\scripts"

$stages = @(
    "01a_soil_background.py",
    "01b_pk_without_n.py",
    "01c_n_response_gr.py",
    "01d_p_response.py",
    "01e_k_response.py",
    "02a_2017_n_rate_response.py",
    "02b_2017_micronutrient_support.py",
    "03a_2018_timing.py",
    "03b_2018_fym_reduced_n.py",
    "03c_2018_udp_reduced_n.py",
    "03d_2018_pcu_full_n.py",
    "03e_2018_pcu_reduced_n.py",
    "03f_2018_pcu_rate_comparison.py",
    "04a_2018_demo.py",
    "05a_2019_trial_timing_v8.py",
    "05b_2019_trial_timing_v6_v10.py",
    "06a_2019_demo_hybrid.py",
    "06b_2019_demo_opv.py"
)

foreach ($stage in $stages) {
    Write-Host "`n===== RUNNING $stage =====" -ForegroundColor Cyan
    & python ".\$stage"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAILED: $stage" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
Write-Host "`n===== ALL STAGES COMPLETED =====" -ForegroundColor Green
