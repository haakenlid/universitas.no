""" Settings for local development """

from .dev import *  # noqa
from .dev import (
    WEBPACK_LOADER, DEBUG, INSTALLED_APPS, MIDDLEWARE_CLASSES, DATABASES, env
)
from .setting_helpers import Environment
DEFAULT_FROM_EMAIL = 'localemail@localhost'
# DATABASES['prodsys'].update({'HOST': 'localhost', })
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

RUNSERVERPLUS_SERVER_ADDRESS_PORT = '0.0.0.0:8000'
ALLOWED_HOSTS = '*'
# TOOLBAR CONFIGURATION
INSTALLED_APPS += ['debug_toolbar', ]
MIDDLEWARE_CLASSES += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]

DEBUG_TOOLBAR_PATCH_SETTINGS = False

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STATIC_ROOT = env.STATIC_DIR or '/static/'
STATIC_URL = '/static/'


aws = Environment('AWS')
try:
    AWS_STORAGE_BUCKET_NAME = aws.storage_bucket_name
    AWS_ACCESS_KEY_ID = aws.access_key_id
    AWS_SECRET_ACCESS_KEY = aws.secret_access_key

    # AMAZON WEB SERVICES
    DEFAULT_FILE_STORAGE = 'utils.aws_custom_storage.MediaStorage'
    THUMBNAIL_STORAGE = 'utils.aws_custom_storage.ThumbStorage'

    AWS_S3_HOST = 's3.eu-central-1.amazonaws.com'
    AWS_S3_CUSTOM_DOMAIN = AWS_STORAGE_BUCKET_NAME  # cname
    AWS_S3_SECURE_URLS = False
    AWS_S3_USE_SSL = False

    MEDIA_URL = "http://{host}/{media}/".format(
        host=AWS_S3_CUSTOM_DOMAIN, media='media', )

except AttributeError:
    # Use File system in local development instead of Amanon S3
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    THUMBNAIL_STORAGE = DEFAULT_FILE_STORAGE
    MEDIA_ROOT = env.MEDIA_DIR or '/media/'
    MEDIA_URL = '/media/'


if DEBUG:
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True
    }

# DATABASE_ROUTERS = []
DATABASES['prodsys'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': 'prodsys.sqlite3.db',
}

WEBPACK_LOADER['DEFAULT'].update({
    'CACHE': not DEBUG,
    'POLL_INTERVAL': 0.5,
    'TIMEOUT': None,
    # 'IGNORE': ['.+\.hot-update.js', '.+\.map']
})