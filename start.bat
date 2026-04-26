@echo off
echo.
echo   House Helper — Starting...
echo.

call .venv\Scripts\activate.bat

:: Start backend
start "HouseHelper-Backend" cmd /c "cd backend && uvicorn main:app --port 8040"
echo [OK] Backend starting on port 8040

:: Wait a moment
timeout /t 3 /nobreak >nul

:: Start frontend
start "HouseHelper-Frontend" cmd /c "cd frontend && npm run dev"
echo [OK] Frontend starting

timeout /t 2 /nobreak >nul
echo.
echo   App is running — open http://localhost:5173
echo.
echo   Close the terminal windows to stop.
echo.
