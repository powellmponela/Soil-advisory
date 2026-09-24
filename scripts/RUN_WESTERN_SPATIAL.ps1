$ErrorActionPreference = "Stop"
Set-Location "D:\dss\SOIL ADVISORY"

$stages = @(
    "scripts\1c_extract_narc_western_highres_primary.py",
    "scripts\4c_run_quefts_western_highres_primary.py",
    "scripts\5a_build_nsaf_n_management_training.py",
    "scripts\5b_predict_western_n_demand_savings.py",
    "scripts\6a_map_western_ae_and_gains.py"
)

foreach ($stage in $stages) {
    Write-Host "`n===== RUNNING $stage =====" -ForegroundColor Cyan
    python ".\$stage"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAILED: $stage" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`n===== COMPLETED =====" -ForegroundColor Green
