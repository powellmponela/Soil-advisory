@echo off
echo ========================================================
echo SOIL ADVISORY - DSS Sequential Execution Pipeline
echo ========================================================
echo.

set SCRIPTS_DIR=scripts
set R_SCRIPT=Rscript

echo [1/9] Stage 1c - Extracting primary high-res NARC/DSM soil data...
python %SCRIPTS_DIR%\1c_extract_narc_western_highres_primary.py
if %ERRORLEVEL% neq 0 goto :error

echo [2/9] Stage 2a - Matching 2018 trials to NARC...
python %SCRIPTS_DIR%\2a_match_2018_trials_to_narc.py
if %ERRORLEVEL% neq 0 goto :error

echo [3/9] Stage 2b - Matching 2019 demos and controls...
python %SCRIPTS_DIR%\2b_match_2019_demos_and_controls.py
if %ERRORLEVEL% neq 0 goto :error

echo [4/9] Stage 2c - Assigning standard farmer IDs...
python %SCRIPTS_DIR%\2c_assign_farmer_ids.py
if %ERRORLEVEL% neq 0 goto :error

echo [5/9] Stage 4c - Running QUEFTS model for high-res pixels...
%R_SCRIPT% %SCRIPTS_DIR%\4c_run_quefts_western_highres_primary.R
if %ERRORLEVEL% neq 0 (
    echo Note: Ensure R is installed and in your PATH to run .R scripts.
    goto :error
)

echo [6/9] Stage 6 - Consolidating 3-year harmonized trials...
python %SCRIPTS_DIR%\6_consolidate_3year_trials.py
if %ERRORLEVEL% neq 0 goto :error

echo [7/9] Stage 7 - Training NUE Random Forest Model...
python %SCRIPTS_DIR%\7_train_nue_rf_model.py
if %ERRORLEVEL% neq 0 goto :error

echo [8/9] Stage 8 - Generating spatial impact maps...
python %SCRIPTS_DIR%\8_generate_spatial_impact_maps.py
if %ERRORLEVEL% neq 0 goto :error

echo [9/9] Stage 9 - Calculating national impact...
python %SCRIPTS_DIR%\9_calculate_national_impact.py
if %ERRORLEVEL% neq 0 goto :error

echo.
echo ========================================================
echo SUCCESS! Full core pipeline completed.
echo ========================================================
goto :EOF

:error
echo.
echo ========================================================
echo ERROR: Pipeline execution halted.
echo Please check the logs above for details.
echo ========================================================
exit /b 1
