@echo off
title Job Aggregator Desktop
cd /d "%~dp0"
if exist "dist\JobAggregator\JobAggregator.exe" (
    echo Starting Job Aggregator Desktop...
    start "" "dist\JobAggregator\JobAggregator.exe"
) else (
    echo Starting Job Aggregator via Python...
    python desktop_main.py
)
