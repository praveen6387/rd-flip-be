web: python manage.py migrate && gunicorn rd_flip_be.wsgi:application --bind 0.0.0.0:${PORT:-8000}
