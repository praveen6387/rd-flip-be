"""
WSGI entry point for rd-flip-be.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rd_flip_be.settings")

application = get_wsgi_application()
