"""
Django settings per gestionale_presenze.
"""
import os
import environ
from pathlib import Path

# --- 1. SETUP BASE PATHS ---
# Poiché settings.py è in src/config/, dobbiamo salire di 2 livelli per trovare la root di src
# E di 3 livelli per la root del progetto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Inizializza environment variables
env = environ.Env()
# Legge il file .env che metteremo nella root principale
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# --- 2. SECURITY ---
SECRET_KEY = env('SECRET_KEY', default='chiave-non-sicura-per-dev-locale')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# --- 3. APPS INSTALLATE ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Librerie Terze Parti
    'django_htmx',
    
    # Le Nostre Apps (Le creeremo tra poco)
    'apps.core',
    'apps.anagrafica',
    'apps.presenze',
    'apps.bi',
    'apps.ingestion',
    'apps.export',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware', # Middleware HTMX
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'src/templates')], # Cartella templates custom
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

WSGI_APPLICATION = 'config.wsgi.application'

# --- 4. DATABASE ---
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

# --- 5. AUTH E PASSWORD ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

# Usiamo il nostro modello Utente Custom
AUTH_USER_MODEL = 'core.User' 

# --- 6. INTERNATIONALIZATION ---
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

# --- 7. STATIC & MEDIA ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_cdn')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'src/static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media_cdn')

# --- 8. CONFIGURAZIONE DEFAULT ID ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'