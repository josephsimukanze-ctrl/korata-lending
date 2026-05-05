"""
Django settings for korata_lending project.
"""

from pathlib import Path
import os
import dj_database_url
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== SECURITY HARDENING ====================

# 🔐 SECRET KEY - Must be environment variable in production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY and not os.getenv('DEBUG', 'True') == 'True':
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set in production")

# Use a secure fallback only for development
if not SECRET_KEY:
    SECRET_KEY = 'django-insecure-unsafe-secret-key-for-dev-only'

DEBUG = os.getenv('DEBUG', 'True') == 'True'

# 🎯 ALLOWED HOSTS - Strict control
if DEBUG:
    ALLOWED_HOSTS = [
        '127.0.0.1',
        'localhost',
        '10.116.15.142',
        'commissive-syntonically-jayla.ngrok-free.dev',
        '*.ngrok-free.dev',
        '*.ngrok.io',
    ]
else:
    # Production - must be set via environment variable
    raw_hosts = os.getenv('ALLOWED_HOSTS')
    if not raw_hosts:
        # Default for Render
        ALLOWED_HOSTS = ['.onrender.com', 'localhost', '127.0.0.1']
    else:
        ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(',') if host.strip()]

# 🔐 CSRF Trusted Origins
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.ngrok-free.dev',
        'http://*.ngrok-free.dev',
        'https://commissive-syntonically-jayla.ngrok-free.dev',
        'http://commissive-syntonically-jayla.ngrok-free.dev',
        'https://*.ngrok.io',
        'http://*.ngrok.io',
    ]
else:
    # Production for Render
    csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
    if csrf_origins:
        CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',') if origin.strip()]
    else:
        CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

# 🔹 Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Add this for templates
    
    # Third-party apps
    'crispy_forms',
    'crispy_tailwind',
    'corsheaders',
    'rest_framework',
    
    # Local apps
    'users',
    'clients',
    'collateral',
    'loans',
    'payments',
    'core',
    'reports',
    'notifications',
    'auction',
    'backup',
]

# Crispy Forms Settings
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# 🔹 Security Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files
    'corsheaders.middleware.CorsMiddleware',  # CORS support
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
]

# Only add custom middleware if they exist
try:
    import core.middleware
    MIDDLEWARE.extend([
        'core.middleware.SessionIdleTimeoutMiddleware',
        'core.middleware.ActivityTrackingMiddleware',
        'core.middleware.SecurityHeadersMiddleware',
        'users.middleware.UserPreferencesMiddleware',
    ])
except ImportError:
    pass  # Custom middleware not available

# ==================== DATABASE CONFIGURATION ====================
# PostgreSQL for production, SQLite for development

# Database configuration
if os.getenv('DATABASE_URL'):
    # Production on Render
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            ssl_require=not DEBUG  # Require SSL in production
        )
    }
else:
    # Local development with PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'korata_lending'),
            'USER': os.getenv('DB_USER', 'korata_user'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'korata123'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# ==================== TIMEZONE HANDLING ====================
USE_TZ = True  # Always use timezone-aware datetimes
TIME_ZONE = 'Africa/Lusaka'  # or 'Africa/Nairobi', 'UTC'
USE_I18N = True
LANGUAGE_CODE = 'en-us'

# ==================== SESSION TIMEOUT SETTINGS ====================
SESSION_COOKIE_AGE = 1500  # 25 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
IDLE_TIMEOUT_SECONDS = 120  # 2 minutes in seconds

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Custom session settings
SESSION_ACTIVITY_KEY = 'last_activity'
SESSION_IDLE_WARNING_TIME = 100

# 🔐 HTTPS Security (Production only)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# 🔐 CSRF Settings
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# 🔐 CORS Settings
CORS_ALLOWED_ORIGINS = [
    'https://*.onrender.com',
    'https://*.ngrok-free.dev',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True

# 🔐 Password Validation - Enhanced
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# 📦 Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 📁 Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# 🔑 Default PK
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 👤 Custom User
AUTH_USER_MODEL = 'users.CustomUser'

# 🔐 Auth URLs
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/users/login/'

# 🔐 Authentication Backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# 📧 Email (secure)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', 30))

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Korata Lending <noreply@korata.com>')
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000' if DEBUG else 'https://yourdomain.com')

# 🎨 Messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# 🪵 Logging
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} - {levelname} - {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'security.log',
            'formatter': 'security',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ⚡ Cache
if not DEBUG and os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# 📤 Upload security
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
DATA_UPLOAD_MAX_NUMBER_FILES = 100
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# 🖨️ PDF Settings
XHTML2PDF_TEMP = BASE_DIR / 'tmp'
XHTML2PDF_TEMP.mkdir(exist_ok=True)

# 🔐 Silk profiling (only in development)
if DEBUG:
    try:
        INSTALLED_APPS.append('silk')
        MIDDLEWARE.insert(1, 'silk.middleware.SilkyMiddleware')
    except ImportError:
        pass

# Application definition
ROOT_URLCONF = 'korata_lending.urls'

# 🔹 Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'django.templatetags.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'korata_lending.wsgi.application'

# ==================== PRODUCTION VALIDATION ====================
if not DEBUG:
    # Validate required environment variables
    required_vars = ['DJANGO_SECRET_KEY', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Ensure HTTPS in production
    if not SECURE_SSL_REDIRECT:
        raise ValueError("SECURE_SSL_REDIRECT must be True in production")

# ==================== AI CONFIGURATIONS ====================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'tinyllama')

# ==================== SMS PROVIDER CONFIGURATIONS ====================
AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', '')
AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY', '')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
SMS_SENDER_ID = os.getenv('SMS_SENDER_ID', 'Korata')