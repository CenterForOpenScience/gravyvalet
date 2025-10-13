"""settings from environment variables
"""

import os
import sys


TESTING = "test" in sys.argv
DEBUG = bool(os.environ.get("DEBUG"))  # any non-empty value enables debug mode
SECRET_KEY = os.environ.get("SECRET_KEY")  # used by django for cryptographic signing
ALLOWED_HOSTS = list(filter(bool, os.environ.get("ALLOWED_HOSTS", "").split(",")))
CORS_ALLOWED_ORIGINS = tuple(
    filter(bool, os.environ.get("CORS_ALLOWED_ORIGINS", "").split(","))
)
SENTRY_DSN = os.environ.get("SENTRY_DSN")
SECURE_PROXY_SSL_HEADER = os.environ.get("SECURE_PROXY_SSL_HEADER")
NEW_RELIC_CONFIG_FILE = os.environ.get("NEW_RELIC_CONFIG_FILE")
NEW_RELIC_ENVIRONMENT = os.environ.get("NEW_RELIC_ENVIRONMENT")


###
# databases

POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

OSFDB_NAME = os.environ.get("OSFDB_NAME", "osf")
OSFDB_USER = os.environ.get("OSFDB_USER", "postgres")
OSFDB_PASSWORD = os.environ.get("OSFDB_PASSWORD", "")
OSFDB_HOST = os.environ.get("OSFDB_HOST")
OSFDB_PORT = os.environ.get("OSFDB_PORT", "5432")
OSFDB_CONN_MAX_AGE = os.environ.get("OSFDB_CONN_MAX_AGE", 0)
OSFDB_SSLMODE = os.environ.get("OSFDB_SSLMODE", "prefer")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis://192.168.168.167:6379")

###
# for interacting with osf

OSF_SENSITIVE_DATA_SECRET = os.environ.get("OSF_SENSITIVE_DATA_SECRET", "")
OSF_SENSITIVE_DATA_SALT = os.environ.get("OSF_SENSITIVE_DATA_SALT", "")
OSF_HMAC_KEY = os.environ.get("OSF_HMAC_KEY")
OSF_HMAC_EXPIRATION_SECONDS = int(os.environ.get("OSF_HMAC_EXPIRATION_SECONDS", 110))
OSF_BASE_URL = os.environ.get("OSF_BASE_URL", "https://osf.example")
OSF_API_BASE_URL = os.environ.get("OSF_API_BASE_URL", "https://api.osf.example")
OSF_AUTH_COOKIE_NAME = os.environ.get("OSF_AUTH_COOKIE_NAME", "osf")
OSF_AUTH_COOKIE_SECRET = os.environ.get("OSF_AUTH_COOKIE_SECRET", "CHANGEME")
SESSION_COOKIE_DOMAIN = os.environ.get("SESSION_COOKIE_DOMAIN", None)
SESSION_COOKIE_SECURE = os.environ.get(
    "SESSION_COOKIE_SECURE", True
)  # Change to False for local dev
SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = os.environ.get(
    "SESSION_COOKIE_SAMESITE", "None"
)  # Change to "Lax" for local dev

###
# amqp/celery

AMQP_BROKER_URL = os.environ.get(
    "AMQP_BROKER_URL", "amqp://guest:guest@192.168.168.167:5672"
)
GV_QUEUE_NAME_PREFIX = os.environ.get("GV_QUEUE_NAME_PREFIX", "gravyvalet_tasks")
OSF_BACKCHANNEL_QUEUE_NAME = os.environ.get(
    "OSF_BACKCHANNEL_QUEUE_NAME", "account_status_changes"
)

SILKY_PYTHON_PROFILER = os.environ.get("SILKY_PYTHON_PROFILER", False)

###
# credentials encryption secrets and parameters
#
# to rotate credentials encryption secrets (and settings):
# 1. update environment:
#    - set GRAVYVALET_ENCRYPT_SECRET to a new, long, random string (...no commas, tho)
#    - add the old secret to GRAVYVALET_ENCRYPT_SECRET_PRIORS (comma-separated list)
#    - (optional) update key-derivation parameters with best practices du jour
# 2. call `.rotate_encryption()` on every `ExternalCredentials` (perhaps via
#    celery tasks in `addon_service.tasks.key_rotation`)
# 3. remove the old secret from GRAVYVALET_ENCRYPT_SECRET_PRIORS
GRAVYVALET_ENCRYPT_SECRET: str | None = os.environ.get("GRAVYVALET_ENCRYPT_SECRET")
GRAVYVALET_ENCRYPT_SECRET_PRIORS = tuple(
    filter(bool, os.environ.get("GRAVYVALET_ENCRYPT_SECRET_PRIORS", "").split(","))
)
# optional overrides for scrypt key derivation parameters (when unset, use sensible defaults)
# see https://datatracker.ietf.org/doc/html/rfc7914#section-2
GRAVYVALET_SALT_BYTE_COUNT = int(os.environ.get("GRAVYVALET_SALT_BYTE_COUNT", 17))
GRAVYVALET_SCRYPT_COST_LOG2 = int(os.environ.get("GRAVYVALET_SCRYPT_COST_LOG2", 17))
GRAVYVALET_SCRYPT_BLOCK_SIZE = int(os.environ.get("GRAVYVALET_SCRYPT_BLOCK_SIZE", 8))
GRAVYVALET_SCRYPT_PARALLELIZATION = int(
    os.environ.get("GRAVYVALET_SCRYPT_PARALLELIZATION", 1)
)
# size of the derived-key cache (set to "0" to disable caching)
GRAVYVALET_DERIVED_KEY_CACHE_SIZE = int(
    os.environ.get("GRAVYVALET_DERIVED_KEY_CACHE_SIZE", 512)
)
# END credentials encryption secrets and parameters
###
