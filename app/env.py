"""settings from environment variables
"""

import os


POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

SECRET_KEY = os.environ.get("SECRET_KEY")
OSF_HMAC_KEY = os.environ.get("OSF_HMAC_KEY")

OSF_BASE_URL = os.environ.get("OSF_BASE_URL", "https://osf.example")
OSF_API_BASE_URL = os.environ.get("OSF_API_BASE_URL", "https://api.osf.example")

# any non-empty value enables debug mode:
DEBUG = bool(os.environ.get("DEBUG"))

# comma-separated list:
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
