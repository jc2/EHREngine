import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ehrengine.settings.dev")
django.setup()

from django.core.asgi import get_asgi_application

from mcp_server.server import mcp
from mcp_server.auth import PatientAuthMiddleware

django_app = get_asgi_application()
mcp_app = PatientAuthMiddleware(mcp.streamable_http_app())


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        await mcp_app(scope, receive, send)
    elif scope["type"] in ("http", "websocket") and scope.get("path", "").startswith(
        "/mcp"
    ):
        await mcp_app(scope, receive, send)
    else:
        await django_app(scope, receive, send)
