@echo off
echo ============================================
echo  Bank Churner Analytics — Web Dashboard
echo ============================================
echo.

:: Install deps if needed
pip show fastapi >nul 2>&1 || (
    echo Installing dependencies...
    pip install -r requirements_web.txt
)

echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop.
echo.
start "" "http://localhost:8000"
python -m uvicorn server:app --reload --port 8000
