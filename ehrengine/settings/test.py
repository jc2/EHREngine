from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ehrengine_test",
        "USER": "ehrengine",
        "PASSWORD": "ehrengine_dev",
        "HOST": "localhost",
        "PORT": "5433",
    }
}
