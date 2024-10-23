from pathlib import Path

import environ
import sentry_sdk
from django.contrib import messages

env = environ.Env()

# BASE SETTINGS ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ENVIRONMENT = env.str("ENVIRONMENT")
SECRET_KEY = env.str("SECRET_KEY")
APPLICATION_DOMAIN = env.str("APPLICATION_DOMAIN")
ALLOWED_HOSTS = [APPLICATION_DOMAIN]
RELEASE_DATETIME = env.str("RELEASE_DATETIME", "DD/MM/YY HH:MM")

if ENVIRONMENT == "prod":
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [f"https://{APPLICATION_DOMAIN}"]
    sentry_sdk.init()

# APPLICATION DEFINITION ------------------------------------------------------
INSTALLED_APPS = [
    "competitions.apps.CompetitionsConfig",
    "core.apps.CoreConfig",
    "clubs.apps.ClubsConfig",
    "users.apps.UsersConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "ddtrace.contrib.django",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_htmx",
    "crispy_forms",
    "crispy_bootstrap5",
    "guardian",
    "django_rq",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "core.middleware.HtmxMessageMiddleware",
]
ROOT_URLCONF = "ultihub.urls"
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
                "core.context_processors.app_version_processor",
                "users.context_processors.user_managed_clubs",
            ],
        },
    },
]
WSGI_APPLICATION = "ultihub.wsgi.application"

MESSAGE_TAGS = {
    messages.DEBUG: "bg-light",
    messages.INFO: "text-white bg-primary",
    messages.SUCCESS: "text-white bg-success",
    messages.WARNING: "text-dark bg-warning",
    messages.ERROR: "text-white bg-danger",
}

# DATABASE --------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("DATABASE_NAME"),
        "USER": env.str("DATABASE_USER"),
        "PASSWORD": env.str("DATABASE_PASSWORD"),
        "HOST": env.str("DATABASE_HOST"),
        "PORT": "5432",
    }
}

# AUTHENTICATION ---------------------------------------------------------------
SITE_ID = 1
LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = "users.adapters.SocialAccountAdapter"
SOCIALACCOUNT_ONLY = True
ACCOUNT_EMAIL_REQUIRED = True
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "guardian.backends.ObjectPermissionBackend",
]
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "APP": {
            "client_id": env.str("GOOGLE_CLIENT_ID"),
            "secret": env.str("GOOGLE_CLIENT_SECRET"),
        },
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

# INTERNATIONALIZATION --------------------------------------------------------
# https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Prague"
USE_I18N = False
USE_TZ = True

# STATIC FILES ----------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = Path("/app/static")
if ENVIRONMENT == "dev":
    STATICFILES_DIRS = [BASE_DIR / "static"]

# DJANGO ----------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# LOGGING ---------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(asctime)s %(levelname)s %(message)s %(name)s"
                " %(dd.service)s %(dd.env)s %(dd.version)s %(dd.trace_id)s %(dd.span_id)s"
            ),
        },
        "simple": {"format": "%(levelname)s %(name)s: %(message)s"},
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "ddtrace": {
            "handlers": ["console"],
            "level": "WARNING",
        },
        "gunicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

if ENVIRONMENT == "prod":
    LOGGING.update(
        {
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                },
            }
        }
    )
else:
    LOGGING.update(
        {
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "simple",
                },
            }
        }
    )


# TESTING AND DEBUG ----------------------------------------------------------
DEBUG = env.bool("DEBUG", ENVIRONMENT in ["dev", "test"])

if ENVIRONMENT != "test":
    INSTALLED_APPS = [
        *INSTALLED_APPS,
        "debug_toolbar",
    ]
    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE,
    ]


# CRISPY FORMS ----------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


# EMAIL SETTINGS --------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

# REDIS QUEUE -----------------------------------------------------------------
RQ_QUEUES = {
    "default": {
        "URL": "redis://redis:6379/0",
        "DEFAULT_TIMEOUT": 360,
    }
}
