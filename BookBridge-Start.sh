#!/usr/bin/env bash
# BookBridge one-click start (macOS / Linux)
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

echo "============================================================"
echo "   BookBridge - one click start"
echo "============================================================"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "[X] Python 3 is not installed. Install it and try again."
    exit 1
fi

if [ ! -x "venv/bin/python" ]; then
    echo "[1/5] Creating virtual environment..."
    "$PYTHON" -m venv venv
else
    echo "[1/5] Virtual environment found."
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "[2/5] Installing requirements..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[3/5] Creating .env from .env.example ..."
    cp .env.example .env
else
    echo "[3/5] Using existing .env"
fi

echo "[4/5] Applying database migrations..."
python manage.py migrate --noinput

echo "[5/5] Loading demo data (only if the database is empty)..."
python manage.py seed_demo --if-empty || true

echo
echo "============================================================"
echo "   Open http://127.0.0.1:8000"
echo "   Demo login:  demo      Password: bookbridge123"
echo "   Stop the server with CTRL + C"
echo "============================================================"
echo

( sleep 5; command -v open >/dev/null 2>&1 && open http://127.0.0.1:8000 || true ) &
exec python manage.py runserver 127.0.0.1:8000
