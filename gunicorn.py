# Gunicorn runtime configuration

workers = 1

# Environment variables
raw_env = [
    "DJANGO_SETTINGS_MODULE=primerdesign.production"
]
