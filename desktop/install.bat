@echo off
title Job Aggregator Installer
cd /d "%~dp0"
echo Unblocking setup files...
powershell -Command "Unblock-File -Path '.\dist\JobAggregatorSetup.exe' -ErrorAction SilentlyContinue; Unblock-File -Path '.\dist\JobAggregator\JobAggregator.exe' -ErrorAction SilentlyContinue"
if exist "dist\JobAggregatorSetup.exe" (
    echo Starting JobAggregatorSetup.exe...
    start "" "dist\JobAggregatorSetup.exe"
) else (
    echo JobAggregatorSetup.exe not found in dist.
    pause
)
