import os
from pathlib import Path

# Percorso base del progetto
BASE_DIR = Path(__file__).resolve().parent.parent

# Sicurezza
SECRET_KEY = 'django-insecure-e-2$+*x5)owa0l1y3to#kq4xul0r_-o1kmtktsym1g6(2kj^v9'
DEBUG = True
ALLOWED_HOSTS = ['studio3srl.pythonanywhere.com', 'localhost', '127.0.0.1']

# Applicazioni installate
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Le tue App
    'apps.core.apps.CoreConfig', # Gestione Utenti Personalizzati
    'apps.anagrafica',           # Aziende e Dipendenti
    'apps.presenze',             # Calendario 2026 e LUL
    'apps.bi',
    'apps.ingestion',
    'apps.export',
    'apps.importer',
]

MIDDLEWARE = [
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
        'DIRS': [BASE_DIR / 'templates'],
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

# Database SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Validazione Password
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Localizzazione (Impostata per l'Italia)
LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True

# File Statici (CSS, JS)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# --- GESTIONE MEDIA (PDF STACOS E LUL) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Modello Utente Personalizzato
AUTH_USER_MODEL = 'core.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_generale'

# --- CONFIGURAZIONE EMAIL UNIFICATA (ARUBA) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtps.aruba.it'
EMAIL_PORT = 465
EMAIL_USE_SSL = True   # Aruba sulla 465 richiede SSL
EMAIL_USE_TLS = False  # Deve essere False se SSL è True
EMAIL_HOST_USER = 'info@studio3lamezia.it'
EMAIL_HOST_PASSWORD = 'viamiceli41A*' 
DEFAULT_FROM_EMAIL = 'Studio3 SRL <info@studio3lamezia.it>'