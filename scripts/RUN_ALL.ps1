cd "D:\dss\SOIL ADVISORY\scripts"

$stages = @(
    "0a_nsaf_maize_ingest.py",
    "1a_nsaf_soil_background_explore.py",
    "1b_nsaf_n_omission_reference_explore.py",
    "1c_nsaf_p_omission_vs_zero_explore.py",
    "1d_nsaf_k_omission_vs_zero_explore.py",
    "1e_nsaf_000_three_omissions_boxplots.py",
    "1f_nsaf_000_omissions_gr_plot_map.py",
    "1g_nsaf_npk_limited_yield_and_ae.py"
)

foreach ($stage in $stages) {
    Write-Host "`n===== RUNNING $stage =====" -ForegroundColor Cyan
    & python ".\$stage"
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "`nFAILED: $stage (exit code $code)" -ForegroundColor Red
        exit $code
    }
}
Write-Host "`n===== 0a-1g COMPLETED =====" -ForegroundColor Green
