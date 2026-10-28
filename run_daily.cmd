@echo off
cd /d "%~dp0"
py -3 daily_report.py
if errorlevel 1 (
  echo Report failed. See the error above.
) else (
  start "" "%~dp0output\latest.html"
)
pause
