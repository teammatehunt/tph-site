"""
ASGI config for tph project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

django_asgi_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ChannelNameRouter, ProtocolTypeRouter, URLRouter

import puzzles.routing

server_environment = os.environ.get("SERVER_ENVIRONMENT", "dev")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"tph.settings.{server_environment}")

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                puzzles.routing.websocket_urlpatterns,
            )
        ),
    }
)
