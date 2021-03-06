""" Django settings for universitas_no project. """

from django.utils.translation import ugettext_lazy as _

from .email_settings import *  # noqa
from .file_settings import *  # noqa
from .logging_settings import LOGGING  # noqa
from .setting_helpers import Environment
from .setting_helpers import joinpath as path

env = Environment(strict=False)
redis_host = env.redis_host or 'redis'
redis_port = env.redis_port or 6379

TASSEN_DESKEN_LOGIN = env.desken_login
TASSEN_DESKEN_PATH = env.desken_path
EXPRESS_SERVER_URL = 'http://express:9000'

DEBUG = True if env.debug.lower() == 'true' else False
TEMPLATE_DEBUG = DEBUG
SITE_URL = env.site_url or 'www.example.com'
SECRET_KEY = env.secret_key
ALLOWED_HOSTS = env.allowed_hosts.split(',')
SILENCED_SYSTEM_CHECKS = ["1_8.W001"]

# DJANGO ALLAUTH
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = False
ACCOUNT_LOGOUT_REDIRECT_URL = '/auth/login/'
# SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'utils.auth.AutoConnectSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        'METHOD': 'js_sdk',
        'SCOPE': ['email'],
        'VERIFIED_EMAIL': True,
        'VERSION': 'v2.5',
    }
}
FACEBOOK_APP_ID = 1936304073248701
FACEBOOK_PAGE_ID = 273358471969
FACEBOOK_DOMAIN_VERIFICATION = 'hy9lkh9i5a4ia332dj5xuayvmxc00x'
SITE_ID = 1
LOGIN_URL = '/auth/login/'
LOGOUT_URL = '/'
LOGIN_REDIRECT_URL = '/prodsys/#'

dcapv = 'django.contrib.auth.password_validation'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': f'{dcapv}.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': f'{dcapv}.CommonPasswordValidator'},
    {'NAME': f'{dcapv}.NumericPasswordValidator'},
]

# DJANGO REST FRAMEWORK
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.LimitOffsetPagination'
    ),
    'PAGE_SIZE': 50,
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
}
REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'api.user.AvatarUserDetailsSerializer'
}

# CELERY TASK RUNNER
CELERY_TASK_DEFAULT_QUEUE = SITE_URL
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://{}:{}/{}'.format(redis_host, redis_port, 5)
CELERYD_HIJACK_ROOT_LOGGER = False
CELERY_BROKER_TRANSPORT_OPTIONS = {'fanout_prefix': True}

# CELERYBEAT_PID_FILE = '/var/run/celery-%n.pid'
# CELERY_SCHEDULE_FILE = '/var/run/celery-schedule-%n'

# Rabbitmq
CELERY_BROKER_URL = 'amqp://guest:guest@rabbit//?heartbeat=30'
CELERY_BROKER_POOL_LIMIT = 10
CELERY_BROKER_CONNECTION_TIMEOUT = 10

# STATIC_ROOT = 'static'
# MEDIA_ROOT = 'media'

# CUSTOM APPS
INSTALLED_APPS = [
    'apps.issues',
    'apps.contributors',
    'apps.stories',
    'apps.core',
    'apps.photo',
    'apps.frontpage',
    'apps.adverts',
]

# THIRD PARTY APPS
INSTALLED_APPS = [
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    # 'allauth.socialaccount.providers.google',
    'django_extensions',
    'sorl.thumbnail',
    'raven.contrib.django.raven_compat',
    'storages',
    'webpack_loader',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'crispy_forms',
    'django_filters',
] + INSTALLED_APPS

# CORE APPS
INSTALLED_APPS = [
    'django.forms',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
] + INSTALLED_APPS

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

WSGI_APPLICATION = 'universitas.wsgi.application'
ROOT_URLCONF = 'universitas.urls'

# SORL
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_ENGINE = 'apps.photo.cropping.crop_engine.CloseCropEngine'
THUMBNAIL_QUALITY = 75
# Use temporary file upload handler to do some queued local operations before
# saving files to the remote server.
FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler"
]
FILE_UPLOAD_TEMP_DIR = '/var/staging/IMAGES/'  # docker volume location
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o6770
FILE_UPLOAD_PERMISSIONS = 0o664
# FILE_UPLOAD_MAX_MEMORY_SIZE = 1000000  # 1 megabyte
# Enable original file names for resized images.
THUMBNAIL_BACKEND = 'apps.photo.thumb_backend.KeepNameThumbnailBackend'
THUMBNAIL_DEBUG = False
# With boto and amazon s3, we don't check if file exist.
# Automatic overwrite if not found in cache key
THUMBNAIL_FORCE_OVERWRITE = True
THUMBNAIL_PREFIX = 'imgcache/'
THUMBNAIL_REDIS_DB = 1
THUMBNAIL_REDIS_HOST = redis_host
THUMBNAIL_KEY_PREFIX = SITE_URL
THUMBNAIL_URL_TIMEOUT = 3

# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.pg_name or 'postgres',
        'USER': env.pg_user or 'postgres',
        'PASSWORD': env.pg_password or 'postgres',
        'HOST': env.pg_host or 'postgres',
        'PORT': env.pg_port or '',  # Set to empty string for default.
    }
}
# CACHE
CACHE_MIDDLEWARE_KEY_PREFIX = SITE_URL
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://{}:{}/0'.format(redis_host, redis_port),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        },
    },
}

# FOLDERS
# source code folder
BASE_DIR = path()

# Django puts generated translation files here.
LOCALE_PATHS = [path('translation')]
# Extra path to collect static assest such as javascript and css
STATICFILES_DIRS = [env.BUILD_DIR]
# Project wide fixtures to be loaded into database.
FIXTURE_DIRS = [path('fixtures')]

# INTERNATIONALIZATIONh
LANGUAGE_CODE = 'nb'
LANGUAGES = [
    ('nb', _('Norwegian Bokmal')),
    ('nn', _('Norwegian Nynorsk')),
    ('en', _('English')),
]

TIME_ZONE = 'Europe/Oslo'
USE_I18N = True  # Internationalisation (string translation)
USE_L10N = True  # Localisation (numbers and stuff)
USE_TZ = True  # Use timezone
DATE_FORMAT = 'j. F, Y'
DATETIME_FORMAT = 'Y-m-d H:i'
SHORT_DATE_FORMAT = 'Y-m-d'
SHORT_DATETIME_FORMAT = 'y-m-d H:i'
TIME_INPUT_FORMATS = ('%H:%M', '%H', '%H:%M:%S', '%H.%M')
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            path('templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'apps.issues.context_processors.issues',
                'apps.contributors.context_processors.staff',
                'apps.core.context_processors.core',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
]
WEBPACK_LOADER = {
    'DEFAULT': {
        'CACHE': True,
        'BUNDLE_DIR_NAME': './',  # must end with slash
        'STATS_FILE': env.BUILD_DIR + 'webpack-stats.json',
    }
}

NOTEBOOK_ARGUMENTS = [
    '--no-browser', '--port=8888', '--ip=0.0.0.0', '--NotebookApp.token=""',
    '--NotebookApp.password="{}"'.format(env.NOTEBOOK_PASSWORD),
    '--notebook-dir',
    path('notebooks')
]
