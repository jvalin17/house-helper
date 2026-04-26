@echo off
echo.
echo   House Helper — Setting up your career copilot
echo   ─────────────────────────────────────────────
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is required. Download from https://www.python.org/downloads/
    exit /b 1
)
echo [OK] Python found

:: Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is required. Download from https://nodejs.org/
    exit /b 1
)
echo [OK] Node.js found

:: Backend
echo.
echo Setting up backend...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -e ".[dev]"
echo [OK] Backend ready

:: Frontend
echo.
echo Setting up frontend...
cd frontend
call npm install --silent
cd ..
echo [OK] Frontend ready

:: Tests
echo.
echo Running tests...
python -m pytest tests/ -q -m "not network" --tb=no
echo.

echo   ─────────────────────────────────────────────
echo   Setup complete.
echo.
echo   To start: start.bat
echo   Then open http://localhost:5173
echo.
