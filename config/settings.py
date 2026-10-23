from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-me')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,0.0.0.0').split(',')
    if host.strip()
]

# Managed hosts (Render, Railway, Fly, Heroku…) tell us the public hostname at
# runtime — trust it automatically so a deploy works without extra config.
for _variable in ('RENDER_EXTERNAL_HOSTNAME', 'RAILWAY_PUBLIC_DOMAIN', 'FLY_APP_HOST'):
    _host = os.environ.get(_variable)
    if _host and _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

# Needed when the app is served through a proxy / tunnel (e.g. a cloud preview URL).
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

# A deployed site's own public URL is always a trusted origin.
_public_url = os.environ.get('SITE_URL', '').rstrip('/')
if _public_url and _public_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_public_url)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'accounts',
    'books',
    'ai_engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serves compressed static files in production (no nginx needed).
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Never let a browser or proxy cache a rendered page (sellers must always
    # see the listing they just saved).
    'core.middleware.NoStoreHTMLMiddleware',
]

ROOT_URLCONF = 'config.urls'

# Absolute base URL used inside emails (verification + notifications).
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.unread_messages',
                'core.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# MySQL (default) or PostgreSQL is used whenever DB_NAME is configured.
# Set DB_ENGINE=postgres for PostgreSQL.
# Without database credentials the project falls back to a local SQLite file so
# `python manage.py migrate` / `runserver` work out of the box for development.
def _database_from_url(url):
    """Parse postgres://user:pass@host:port/name?sslmode=require into DATABASES.

    The query string matters: Neon and most managed Postgres providers put
    ``sslmode=require`` there and refuse a connection without it. Dropping it
    (as this function used to) made a Neon URL fail with a confusing
    "connection refused" at deploy time.
    """
    from urllib.parse import parse_qs, unquote, urlparse

    parsed = urlparse(url)
    params = {key.lower(): values[-1] for key, values in parse_qs(parsed.query).items()}

    options = {}
    for key in ('sslmode', 'channel_binding', 'connect_timeout', 'options',
                'sslcert', 'sslkey', 'sslrootcert', 'application_name'):
        if params.get(key):
            options[key] = params[key]

    config = {
        'ENGINE': 'django.db.backends.postgresql'
        if parsed.scheme.startswith('postgres')
        else 'django.db.backends.mysql',
        'NAME': (parsed.path or '').lstrip('/') or 'bookbridge',
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or ''),
        # A hosted database (Neon, Render) drops idle connections when it
        # suspends. Health checks make Django notice and reconnect instead of
        # handing the request a dead socket.
        'CONN_MAX_AGE': int(params.get('conn_max_age', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
    if options:
        config['OPTIONS'] = options
    return config


if os.environ.get('DATABASE_URL'):
    DATABASES = {'default': _database_from_url(os.environ['DATABASE_URL'])}
elif os.environ.get('DB_NAME'):
    db_engine = (os.environ.get('DB_ENGINE') or 'mysql').lower()
    backend = (
        'django.db.backends.postgresql'
        if db_engine in ('postgres', 'postgresql')
        else 'django.db.backends.mysql'
    )
    DATABASES = {
        'default': {
            'ENGINE': backend,
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Email
#   Development (default): emails are printed to the console.
#   Production: set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   plus EMAIL_HOST / EMAIL_PORT / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'BookBridge <no-reply@bookbridge.local>')
EMAIL_TIMEOUT = 10

# Set to True to stop "new chat message" emails (useful for tests/demos).
DISABLE_CHAT_EMAILS = os.environ.get('DISABLE_CHAT_EMAILS', 'False').lower() in ('true', '1', 'yes')

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Project-owned static files (icons, manifest assets). Without this, collectstatic
# only picks up the admin's files and our icons 404 in production.
STATICFILES_DIRS = [BASE_DIR / 'static']
# ---------------------------------------------------------------------------
# Demo mode
#   A review deploy needs books, photos and chats on screen without anybody
#   adding them by hand. DEMO_MODE=1 lets `seed_demo` run with DEBUG off.
#   Demo accounts created this way get an unusable password, so the public
#   README password cannot be used to sign in on a live site.
# ---------------------------------------------------------------------------
DEMO_MODE = os.environ.get('DEMO_MODE', 'False').lower() in ('true', '1', 'yes')

# ---------------------------------------------------------------------------
# Uploaded photos (book covers)
#   filesystem - local disk. Fine for development, wiped by a free host on
#                every restart.
#   db         - stored in the database as bytes, so covers survive a redeploy
#                on a free plan with no object storage. Set MEDIA_STORAGE=db.
# ---------------------------------------------------------------------------
MEDIA_STORAGE = os.environ.get('MEDIA_STORAGE', 'filesystem').strip().lower()

STORAGES = {
    'default': {
        'BACKEND': (
            'core.storage.DatabaseStorage'
            if MEDIA_STORAGE == 'db'
            else 'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

LOGIN_URL = 'accounts:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Sessions/cookies hardening when running behind HTTPS in production.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in (
        'true', '1', 'yes'
    )
    # Some PaaS health checks hit the container over plain HTTP.
    SECURE_REDIRECT_EXEMPT = [r'^healthz/?$']
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Logging: everything of level INFO+ goes to the console and to logs/app.log.
# ---------------------------------------------------------------------------
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# ---------------------------------------------------------------------------
# Trust & safety
# ---------------------------------------------------------------------------
# Cache-backed rate limits: (allowed writes, window in seconds). Swap the cache
# backend for Redis in production and these limits follow automatically.
RATE_LIMITS = {
    'chat': (25, 5 * 60),       # messages per 5 minutes
    'listing': (10, 60 * 60),   # new listings per hour
    'report': (5, 60 * 60),     # reports per hour
    'review': (10, 60 * 60),    # seller reviews per hour
    'request': (5, 60 * 60),    # book requests per hour
    'ai': (120, 60 * 60),       # AI helper calls per hour
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'bookbridge-trust',
        'TIMEOUT': 300,
    }
}

# A review is only allowed after a real conversation, and this is the minimum
# number of messages exchanged before the "Rate seller" button appears.
REVIEW_MIN_MESSAGES = 1
