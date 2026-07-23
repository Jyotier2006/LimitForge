import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only")
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "demo.urls"
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "limitforge.django.RateLimitMiddleware",
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
USE_TZ = True

LIMITFORGE = {
    "BACKEND": {"type": "memory"},
    "DEFAULT": {"algorithm": "sliding_window", "limit": 10, "window_seconds": 60},
    "RULES": [
        {
            "name": "strict",
            "pattern": r"^/strict/$",
            "limit": 2,
            "window_seconds": 60,
            "algorithm": "fixed_window",
        }
    ],
    "EXEMPT_PATHS": ["/health/"],
}
