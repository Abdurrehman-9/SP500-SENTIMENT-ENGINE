@echo off
cd /d "%~dp0"
echo [1/2] Running daily market data ingestion...
"%~dp0.venv\Scripts\python.exe" "%~dp0pipeline.py" daily
echo [2/2] Calculating derived market metrics and breadth features...
"%~dp0.venv\Scripts\python.exe" "%~dp0features.py"
echo Daily refresh cycle completed successfully.
exit /b %ERRORLEVEL%
