@echo off
REM BookBridge - one command to bring the app back up on Windows.
REM   scripts\dev_up.bat           preview mode, auto-login as demo
REM   scripts\dev_up.bat --fresh   recreate the demo data first
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Creating the Python environment ^(first run only^)
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
)

.venv\Scripts\python.exe -c "import django, PIL, whitenoise, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
)

echo Applying migrations
.venv\Scripts\python.exe manage.py migrate --noinput

if /I "%~1"=="--fresh" (
    .venv\Scripts\python.exe manage.py seed_demo --reset --with-admin
) else (
    .venv\Scripts\python.exe manage.py seed_demo --if-empty --with-admin
)

echo Starting BookBridge on http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
