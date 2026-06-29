@echo off
echo ======================================================
echo   IMU + Visual Fusion Pipeline ? Startup
echo ======================================================
echo.

REM --- Step 1: Diagnostic ---
echo [1/3] Running pre-flight diagnostic...
D:\ProgramData\anaconda3\envs\hamer\python.exe work\IMU_Fusion\fusion_pipeline.py --check
if %ERRORLEVEL% NEQ 0 goto :check_fail
echo.

REM --- Step 2: Check Unity connection ---
echo [2/3] Listening for Unity heartbeat...
echo   If this hangs, Unity is not running or not sending data
echo   Press Ctrl+C to skip
echo.

REM --- Step 3: Start pipeline ---
echo [3/3] Starting fusion pipeline...
echo   Port 5055 - VisionBridge.cs (curl/spread for OnlyTip 2.3)
echo   Port 8080 - FusionUDPReceiver.cs (fused IMU+visual data)
echo.
echo Controls: q=quit  c=recalibrate
echo.
D:\ProgramData\anaconda3\envs\hamer\python.exe work\IMU_Fusion\fusion_pipeline.py
goto :end

:check_fail
echo.
echo [?] Pre-flight check found issues. Fix them before running.
echo   Run "D:\ProgramData\anaconda3\envs\hamer\python.exe work\IMU_Fusion\diagnose.py" for details
pause

:end
