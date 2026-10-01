import os
from pathlib import Path

from decouple import AutoConfig, Csv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

config = AutoConfig(search_path=str(BASE_DIR.parent))

SECRET_KEY = config('SECRET_KEY')

PLATONUS_ENCRYPTION_KEY = config("PLATONUS_ENCRYPTION_KEY")

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_filters',
    'rest_framework_simplejwt',
    'accounts',
    'journal',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

USE_POSTGRES = config(
    "USE_POSTGRES",
    default=False,
    cast=bool,
)

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB"),
            "USER": config("POSTGRES_USER"),
            "PASSWORD": config("POSTGRES_PASSWORD"),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default=5433, cast=int),
            "OPTIONS": {
                "connect_timeout": 5,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('POSTGRES_DB'),         # Было POSTGRES_DB в .env
#         'USER': config('POSTGRES_USER'),       # Было POSTGRES_USER в .env
#         'PASSWORD': config('POSTGRES_PASSWORD'),
#         'HOST': config('DB_HOST', default='db'),
#         'PORT': config('DB_PORT', default=5432, cast=int),
#     }
# }


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

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL='accounts.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
}







# Адрес Redis для отправки фоновых задач.
CELERY_BROKER_URL = config(
    "CELERY_BROKER_URL",
    default="redis://127.0.0.1:6379/0",
)

# Хранилище результатов задач.
CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND",
    default="redis://127.0.0.1:6379/1",
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Worker не забирает заранее большую пачку задач.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Результаты задач хранятся один час.
# Профили и оценки будут храниться в основной БД.
CELERY_RESULT_EXPIRES = 3600



CELERY_BROKER_CONNECTION_TIMEOUT = 3

CELERY_BROKER_TRANSPORT_OPTIONS = {
    "socket_connect_timeout": 3,
    "socket_timeout": 3,
}