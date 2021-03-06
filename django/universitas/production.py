"""Production settings and globals."""

from .base import *  # noqa
from .setting_helpers import Environment

# DEBUG CONFIGURATION
DEBUG = False
THUMBNAIL_DEBUG = DEBUG

# EMAIL CONFIGURATION
gmail = Environment('GMAIL')
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = gmail.user + '@gmail.com'
EMAIL_HOST_PASSWORD = gmail.password
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# RAVEN / SENTRY
env = Environment()
RAVEN_CONFIG = {
    'dsn': env.raven_dsn,
    'site': env.site_url,
    'release': env.git_sha,
}

# SENTRY_CLIENT = 'raven.contrib.django.raven_compat.DjangoClient'
