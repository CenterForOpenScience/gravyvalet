"""settings from environment variables
"""

import os


POSTGRES_DB = os.environ.get("POSTGRES_DB")
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

OSFDB_NAME = os.environ.get("OSFDB_NAME", "osf")
OSFDB_USER = os.environ.get("OSFDB_USER", "postgres")
OSFDB_PASSWORD = os.environ.get("OSFDB_PASSWORD", "")
OSFDB_HOST = os.environ.get("OSFDB_HOST", "192.168.168.167")
OSFDB_PORT = os.environ.get("OSFDB_PORT", "5432")

SECRET_KEY = os.environ.get("SECRET_KEY")
OSF_HMAC_KEY = os.environ.get("OSF_HMAC_KEY")

# any non-empty value enables debug mode:
DEBUG = bool(os.environ.get("DEBUG"))

# comma-separated list:
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
