from pathlib import Path

from app import env


SECRET_KEY = env.SECRET_KEY
OSF_HMAC_KEY = env.OSF_HMAC_KEY or "lmaoooooo"
OSF_HMAC_EXPIRATION_SECONDS = env.OSF_HMAC_EXPIRATION_SECONDS

GRAVYVALET_ENCRYPT_SECRET: bytes | None = (
    env.GRAVYVALET_ENCRYPT_SECRET.encode() if env.GRAVYVALET_ENCRYPT_SECRET else None
)
GRAVYVALET_ENCRYPT_SECRET_PRIORS: tuple[bytes, ...] = tuple(
    _prior.encode() for _prior in env.GRAVYVALET_ENCRYPT_SECRET_PRIORS
)
GRAVYVALET_SALT_BYTE_COUNT = env.GRAVYVALET_SALT_BYTE_COUNT
GRAVYVALET_SCRYPT_COST_LOG2 = env.GRAVYVALET_SCRYPT_COST_LOG2
GRAVYVALET_SCRYPT_BLOCK_SIZE = env.GRAVYVALET_SCRYPT_BLOCK_SIZE
GRAVYVALET_SCRYPT_PARALLELIZATION = env.GRAVYVALET_SCRYPT_PARALLELIZATION
GRAVYVALET_DERIVED_KEY_CACHE_SIZE = env.GRAVYVALET_DERIVED_KEY_CACHE_SIZE

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.DEBUG

USER_REFERENCE_COOKIE = "osf"
OSF_BASE_URL = env.OSF_BASE_URL.rstrip("/")
OSF_API_BASE_URL = env.OSF_API_BASE_URL.rstrip("/")
ALLOWED_RESOURCE_URI_PREFIXES = {OSF_BASE_URL}
if DEBUG:
    # allow for local osf shenanigans
    ALLOWED_RESOURCE_URI_PREFIXES.update(
        [
            "http://192.168.168.167:5000",
            "http://localhost:5000",
        ]
    )

ALLOWED_HOSTS = env.ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS = env.CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "corsheaders",
    "rest_framework",
    "rest_framework_json_api",
    "addon_service",
]

if DEBUG:
    # run under ASGI locally:
    INSTALLED_APPS.insert(0, "daphne")  # django's reference asgi server
    ASGI_APPLICATION = "app.asgi.application"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# Database settings for PostgreSQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.POSTGRES_DB,
        "USER": env.POSTGRES_USER,
        "PASSWORD": env.POSTGRES_PASSWORD,
        "HOST": env.POSTGRES_HOST,
        "PORT": env.POSTGRES_PORT,
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": env.OSFDB_CONN_MAX_AGE,
        "OPTIONS": {
            "sslmode": env.OSFDB_SSLMODE,
        },
    },
}

if env.OSFDB_HOST:
    DATABASES["osf"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.OSFDB_NAME,
        "USER": env.OSFDB_USER,
        "PASSWORD": env.OSFDB_PASSWORD,
        "HOST": env.OSFDB_HOST,
        "PORT": env.OSFDB_PORT,
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": False,
        "CONN_MAX_AGE": env.OSFDB_CONN_MAX_AGE,
        "OPTIONS": {
            "sslmode": env.OSFDB_SSLMODE,
        },
    }

DATABASE_ROUTERS = ["addon_service.osf_models.db_router.OsfDatabaseRouter"]

REST_FRAMEWORK = {
    "PAGE_SIZE": 101,
    "EXCEPTION_HANDLER": "addon_service.exception_handler.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework_json_api.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
        "rest_framework_json_api.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "addon_service.authentication.GVCombinedAuthentication",
    ),
    "SEARCH_PARAM": "filter[search]",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []  # type: ignore


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"

OSF_SENSITIVE_DATA_SECRET = env.OSF_SENSITIVE_DATA_SECRET
OSF_SENSITIVE_DATA_SALT = env.OSF_SENSITIVE_DATA_SALT


###
# amqp/celery

AMQP_BROKER_URL = env.AMQP_BROKER_URL
OSF_BACKCHANNEL_QUEUE_NAME = env.OSF_BACKCHANNEL_QUEUE_NAME
GV_QUEUE_NAME_PREFIX = env.GV_QUEUE_NAME_PREFIX
