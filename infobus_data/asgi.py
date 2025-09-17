"""
ASGI config for infobus_data project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "infobus_data.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
    }
)
