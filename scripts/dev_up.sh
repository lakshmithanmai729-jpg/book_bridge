#!/usr/bin/env bash
# BookBridge — one command to bring the app back up after a sandbox restart.
#
#   ./scripts/dev_up.sh              # preview mode (auto-login as demo, CSRF off)
#   ./scripts/dev_up.sh --fresh      # also recreate the demo data from scratch
#   ./scripts/dev_up.sh --prod       # production-style run with gunicorn, no CSRF bypass
#
# Everything it does is idempotent: it only reinstalls, migrates or seeds when
# something is actually missing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="${BOOKBRIDGE_VENV:-$HOME/.venv}"
PY="$VENV/bin/python"
MODE="preview"
FRESH="0"

for arg in "$@"; do
    case "$arg" in
        --fresh) FRESH="1" ;;
        --prod)  MODE="prod" ;;
        -h|--help)
            cat <<'USAGE'
BookBridge — start the app in one command.

  ./scripts/dev_up.sh            preview mode: auto-login as demo, CSRF bypass (sandbox/LAN)
  ./scripts/dev_up.sh --fresh    same, but rebuild the demo data first
  ./scripts/dev_up.sh --prod     production mode: gunicorn, real settings

The script creates the Python environment, installs dependencies, migrates the
database, seeds demo data only when the database is empty, collects static files
and then serves the app on 0.0.0.0:8000.
USAGE
            exit 0 ;;
    esac
done

say() { printf '\n\033[1;36m▸ %s\033[0m\n' "$1"; }

# 1. Python environment -------------------------------------------------------
if [ ! -x "$PY" ]; then
    say "Creating the Python environment in $VENV (first run only)"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
fi

if ! "$PY" -c 'import django, PIL, whitenoise, dotenv' >/dev/null 2>&1; then
    say "Installing dependencies"
    "$VENV/bin/pip" install --quiet -r requirements.txt
fi

# 2. Database ----------------------------------------------------------------
say "Applying migrations"
"$PY" manage.py migrate --noinput

if [ "$FRESH" = "1" ]; then
    say "Recreating the demo data"
    "$PY" manage.py seed_demo --reset --with-admin
else
    say "Seeding demo data (only if the database is empty)"
    "$PY" manage.py seed_demo --if-empty --with-admin
fi

# 3. Static files ------------------------------------------------------------
say "Collecting static files"
"$PY" manage.py collectstatic --noinput >/dev/null

# 4. Go ----------------------------------------------------------------------
if [ "$MODE" = "prod" ]; then
    say "Starting gunicorn on 0.0.0.0:8000 (production settings)"
    exec "$VENV/bin/gunicorn" config.wsgi:application \
        --bind 0.0.0.0:8000 --workers 2 --timeout 60
fi

say "Starting the preview server on 0.0.0.0:8000"
exec env PREVIEW_MODE=1 PREVIEW_AUTO_LOGIN=demo "$PY" scripts/preview_server.py
