@echo off
chcp 65001 >nul
title IMU+Visual Fusion Pipeline (Auto-Restart)
echo =============================================
echo   IMU + Visual Fusion Pipeline
echo   Auto-Restart Mode
echo =============================================
echo   Ctrl+C once  = quick restart
echo   Ctrl+C twice = exit
echo =============================================
echo.

:RESTART
echo [%date% %time%] Starting fusion_pipeline.py...
echo.

D:\ProgramData\anaconda3\envs\hamer\python.exe work/IMU_Fusion/fusion_pipeline.py

echo.
echo [%date% %time%] Pipeline exited.
echo [!] Restarting in 3 seconds (Ctrl+C now to stop)...
timeout /t 3 >nul

goto RESTART
