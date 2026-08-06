import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-chvc_&c=dby6wsk0eb3d8daqh4kf196(=i4t7-ie=wg73_b5cs'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Helpdesk',
    'pwa',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
]

ROOT_URLCONF = 'SoporteTI.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SoporteTI.wsgi.application'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'helpdesk',
#         'USER': 'postgres',
#         'PASSWORD': 'root',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }
#Lo comento para el despliuegue xd

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-ec'
TIME_ZONE     = 'America/Guayaquil'
USE_I18N      = True
USE_TZ        = True

# Auth redirects
LOGIN_URL          = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL= '/login/'

# Archivos estáticos
STATIC_URL  = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'SoporteTI/static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Archivos media (adjuntos)
MEDIA_URL  = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Tamaño máximo de subida: 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Session
SESSION_COOKIE_AGE     = 28800  # 8 horas
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ─── PWA (Progressive Web App) ───────────────────────────────────────────────
PWA_APP_NAME        = 'Helpdesk TI'
PWA_APP_DESCRIPTION = 'Sistema de gestión de tickets de soporte técnico'
PWA_APP_THEME_COLOR      = '#012970'
PWA_APP_BACKGROUND_COLOR = '#ffffff'
PWA_APP_DISPLAY     = 'standalone'
PWA_APP_SCOPE       = '/'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL   = '/tickets/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_LANG        = 'es-EC'

PWA_APP_ICONS = [
    {'src': '/static/pwa_icon.png', 'sizes': '192x192', 'type': 'image/png'},
    {'src': '/static/pwa_icon.png', 'sizes': '512x512', 'type': 'image/png'},
]
PWA_APP_ICONS_APPLE = [
    {'src': '/static/pwa_icon.png', 'sizes': '192x192', 'type': 'image/png'},
]
PWA_APP_SPLASH_SCREEN = [
    {'src': '/static/pwa_icon.png', 'media': '(device-width: 320px) and (device-height: 568px)'},
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'staticfiles', 'serviceworker.js')
