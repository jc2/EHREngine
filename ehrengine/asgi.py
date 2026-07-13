import os

import anyio
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ehrengine.settings.dev")
django.setup()

from django.core.asgi import get_asgi_application

from mcp_server.auth import PatientAuthMiddleware
from mcp_server.server import all_mcp, public_mcp

django_app = get_asgi_application()
public_app = PatientAuthMiddleware(public_mcp.streamable_http_app())
all_app = PatientAuthMiddleware(all_mcp.streamable_http_app())

_MCP_APPS = [public_app, all_app]


async def _multiplex_lifespan(scope, receive, send):
    """Forward ASGI lifespan events to all MCP sub-apps in parallel."""

    async def proxy(app, startup_done, shutdown_trigger, shutdown_done):
        to_app_send, to_app_recv = anyio.create_memory_object_stream(4)
        from_app_send, from_app_recv = anyio.create_memory_object_stream(4)

        async def app_receive():
            return await to_app_recv.receive()

        async def app_send(message):
            await from_app_send.send(message)

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                app,
                {"type": "lifespan", "asgi": {"version": "3.0"}},
                app_receive,
                app_send,
            )

            await to_app_send.send({"type": "lifespan.startup"})
            await from_app_recv.receive()  # lifespan.startup.complete
            startup_done.set()

            await shutdown_trigger.wait()
            await to_app_send.send({"type": "lifespan.shutdown"})
            await from_app_recv.receive()  # lifespan.shutdown.complete
            shutdown_done.set()
            tg.cancel_scope.cancel()

    startup_dones = [anyio.Event() for _ in _MCP_APPS]
    shutdown_trigger = anyio.Event()
    shutdown_dones = [anyio.Event() for _ in _MCP_APPS]

    await receive()  # consume lifespan.startup from uvicorn before the inner loop

    async with anyio.create_task_group() as tg:
        for i, app in enumerate(_MCP_APPS):
            tg.start_soon(proxy, app, startup_dones[i], shutdown_trigger, shutdown_dones[i])

        for ev in startup_dones:
            await ev.wait()
        await send({"type": "lifespan.startup.complete"})

        await receive()  # lifespan.shutdown
        shutdown_trigger.set()

        for ev in shutdown_dones:
            await ev.wait()
        await send({"type": "lifespan.shutdown.complete"})
        tg.cancel_scope.cancel()


def _rewrite_path(scope, strip_prefix):
    """Return a copy of scope with the URL prefix stripped, routing to /mcp."""
    path = scope["path"]
    new_path = "/mcp" + path[len(strip_prefix):]
    return {**scope, "path": new_path, "raw_path": new_path.encode()}


async def application(scope, receive, send):
    path = scope.get("path", "")

    if scope["type"] == "lifespan":
        await _multiplex_lifespan(scope, receive, send)
        return

    if scope["type"] not in ("http", "websocket"):
        await django_app(scope, receive, send)
        return

    if path.startswith("/mcp/all"):
        await all_app(_rewrite_path(scope, "/mcp/all"), receive, send)
    elif path.startswith("/mcp/public"):
        await public_app(_rewrite_path(scope, "/mcp/public"), receive, send)
    else:
        await django_app(scope, receive, send)
