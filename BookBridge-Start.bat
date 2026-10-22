@echo off
setlocal
title BookBridge
cd /d "%~dp0"

echo ============================================================
echo    BookBridge - one click start
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [X] Python is not installed or not on PATH.
    echo     Install Python 3.11+ from https://www.python.org/downloads/
    echo     and tick "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/5] Virtual environment found.
)

call "venv\Scripts\activate.bat"

echo [2/5] Installing requirements...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [X] Could not install requirements. Check your internet connection.
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo [3/5] Creating .env from .env.example ...
        copy ".env.example" ".env" >nul
    )
) else (
    echo [3/5] Using existing .env
)

echo [4/5] Applying database migrations...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [X] Migration failed. If you use MySQL, make sure it is running and .env is correct.
    pause
    exit /b 1
)

echo [5/5] Loading demo data ^(only if the database is empty^)...
python manage.py seed_demo --if-empty

echo Preparing static files...
python manage.py collectstatic --noinput >nul 2>nul

echo.
echo ============================================================
echo    Opening http://127.0.0.1:8000
echo    Demo login:  demo      Password: bookbridge123
echo    Stop the server with CTRL + C
echo ============================================================
echo.

start "" /b cmd /c "timeout /t 5 >nul & start "" http://127.0.0.1:8000"
python manage.py runserver 127.0.0.1:8000

echo.
echo Server stopped.
pause
