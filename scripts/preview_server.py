"""Preview server for the Arena live-preview environment (development only).

Usage:
    PREVIEW_MODE=1 PREVIEW_AUTO_LOGIN=demo python scripts/preview_server.py

What it does on top of ``manage.py runserver``:

* ``ALLOWED_HOSTS = ['*']`` so the proxied preview host is accepted,
* cross-site friendly session/CSRF cookie flags,
* drops the CSRF and clickjacking middleware (the preview runs in an iframe),
* optional auto-login so a visitor lands straight in the demo account.

The relaxations are opt-in: without ``PREVIEW_MODE=1`` the script refuses to run,
so it can never be started by accident on a real deployment.
"""
import os
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent

if os.environ.get('PREVIEW_MODE') != '1':
    raise SystemExit(
        'Refusing to start: this server disables CSRF for previews.\n'
        'Run it with PREVIEW_MODE=1 (and optionally PREVIEW_AUTO_LOGIN=<username>).'
    )

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django                                    # noqa: E402  (after sys.path setup)
from django.conf import settings                 # noqa: E402

django.setup()

settings.DEBUG = True
settings.ALLOWED_HOSTS = ['*']
settings.CSRF_TRUSTED_ORIGINS = [
    'https://*.e2b.app',
    'https://*.arena.ai',
    'http://localhost:8000',
]
settings.CSRF_COOKIE_SAMESITE = 'None'
settings.CSRF_COOKIE_SECURE = True
settings.CSRF_COOKIE_HTTPONLY = False
settings.SESSION_COOKIE_SAMESITE = 'None'
settings.SESSION_COOKIE_SECURE = True

settings.MIDDLEWARE = [
    middleware for middleware in settings.MIDDLEWARE
    if middleware not in (
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
    )
]

authentication = 'django.contrib.auth.middleware.AuthenticationMiddleware'
if authentication in settings.MIDDLEWARE:
    settings.MIDDLEWARE.insert(
        settings.MIDDLEWARE.index(authentication) + 1,
        'preview_mw.PreviewMiddleware',
    )

# Media files are served by Django only while DEBUG is on, which is what we want here.
from django.core.management import execute_from_command_line   # noqa: E402

execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000', '--noreload'])
