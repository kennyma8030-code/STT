@echo off
REM One-time setup: creates the Python venv, installs Python + Node deps,
REM and seeds a .env file. Re-running it is safe.

cd /d "%~dp0"

echo ============================================
echo  1/4  Creating Python virtual environment
echo ============================================
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create venv. Is Python 3 installed and on PATH?
        pause
        exit /b 1
    )
) else (
    echo venv already exists, skipping.
)

echo.
echo ============================================
echo  2/4  Installing Python dependencies
echo ============================================
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  3/4  Installing frontend dependencies
echo ============================================
cd frontend
call npm install
if errorlevel 1 (
    echo npm install failed. Is Node.js installed?
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================
echo  4/4  Setting up .env
echo ============================================
if not exist .env (
    copy .env.example .env >nul
    echo Created .env -- opening it in Notepad. Paste your Discord webhook URL, then save and close.
    start /wait notepad .env
) else (
    echo .env already exists, leaving it alone.
)

echo.
echo Done! Edit .env if you haven't, then double-click start.bat to run.
pause
