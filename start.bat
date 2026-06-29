@echo off
REM Double-click this to launch the STT bot (backend + frontend together).
REM It just runs `npm run dev` in the frontend folder, which starts both
REM the FastAPI backend (main.py) and the Vite web UI, and opens the browser.

cd /d "%~dp0frontend"

if not exist node_modules (
    echo node_modules not found. Run setup.bat first.
    pause
    exit /b 1
)

npm run dev
pause
