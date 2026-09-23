"""Django settings for the MIS 3000 learning platform."""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-key-change-me-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "accounts",
    "courses",
    "quizzes",
    "feedback",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite keeps every login, upload, quiz attempt and score on disk between runs.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "USER_ID_FIELD": "id",
}

CORS_ALLOW_ALL_ORIGINS = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 40 * 1024 * 1024

# Explanations are written by a local Ollama model. Nothing leaves the machine and
# no API key is needed. Start Ollama, pull a model, and the platform picks it up.
#   ollama serve
#   ollama pull llama3.1:8b
# If Ollama is not running the platform falls back to its built in rule based writer,
# so uploads, chapters, modules and quizzes keep working either way.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
# Set to "0" to skip Ollama entirely and always use the built in writer.
USE_OLLAMA = os.environ.get("USE_OLLAMA", "1") == "1"
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a

# Pictures found inside an uploaded book are stored and shown beside the explanation for
# the section they came from. Set to "0" to go back to text only uploads.
EXTRACT_BOOK_IMAGES = os.environ.get("EXTRACT_BOOK_IMAGES", "1") == "1"
# Captions are written by the ordinary model from the words printed around the picture.
# Pull a vision model and name it here and the picture itself is described instead:
#   ollama pull llava:7b
#   set OLLAMA_VISION_MODEL=llava:7b
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "")
OLLAMA_CAPTION_TIMEOUT = int(os.environ.get("OLLAMA_CAPTION_TIMEOUT", "90"))
# How many figures in one section get a written caption on a single visit. The rest keep
# the plain caption until the next time the section is opened.
CAPTIONS_PER_VISIT = int(os.environ.get("CAPTIONS_PER_VISIT", "6"))
<<<<<<< HEAD
=======
=======
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
