"""
WSGI config for diploma_smart_parking project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diploma_smart_parking.settings')

# Get the same BASE_DIR as in settings.py
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'

application = get_wsgi_application()
application = WhiteNoise(application)
# Add directories containing static files that should be served
application.add_files(STATIC_ROOT, prefix='static/')
