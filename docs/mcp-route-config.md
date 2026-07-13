# Prompt: Configure MCP Routes and Tool Visibility

Use this prompt verbatim when you want an agent to add, remove, or modify MCP routes and their tool assignments in a project that follows this pattern.

---

## Agent Prompt

You are modifying an MCP server that uses **role-based tool visibility via multiple FastMCP instances**. The project has three files that work together for this pattern:

### Pattern overview

**`mcp_server/roles.py`** — the only place that controls which tools each route exposes. Each route is a plain Python list of imported tool functions. Lists can extend each other (e.g. a "full" list can be defined as a smaller list plus additional items).

**`mcp_server/server.py`** — calls `build_mcp(name, tools)` once per route to create a named FastMCP instance. Tool functions are wrapped with `_traced_async_tool` internally by `build_mcp`; do NOT wrap them in `roles.py`. Export one variable per instance.

**`<project>/asgi.py`** — four touch-points per route:
1. Import the new FastMCP instance from `server.py`.
2. Wrap it: `<name>_app = PatientAuthMiddleware(<instance>.streamable_http_app())`.
3. Add it to `_MCP_APPS` (the list used by the lifespan multiplexer).
4. Add a routing branch in `application()`: `if path.startswith("/mcp/<route>"): await <name>_app(_rewrite_path(scope, "/mcp/<route>"), receive, send)`.

### Critical rules

- `_rewrite_path(scope, "/mcp/<route>")` strips the route prefix so the internal Starlette/FastMCP router always sees `/mcp`. Never omit this call.
- `_MCP_APPS` must contain **every** wrapped app. The lifespan multiplexer fans startup/shutdown to exactly this list; omitting an app means its session manager never initializes and all requests to that route return 500.
- `await receive()` at the top of `_multiplex_lifespan` (before the task group) consumes the `lifespan.startup` event from uvicorn. Do NOT remove or move it — without it the second `receive()` returns startup instead of shutdown, triggering instant session-manager teardown on all routes.
- Tool functions in `roles.py` are imported directly from their source modules. Do not call them; just reference them in the list.
- The string passed to `_rewrite_path` and to `path.startswith(...)` must be identical and must include the `/mcp/` prefix.

---

## How to describe your change

Before making any changes, read the current state of `mcp_server/roles.py`, `mcp_server/server.py`, and `<project>/asgi.py` to understand what routes and tools already exist.

Then accept instructions in any of these forms:

```
Add route /mcp/<name> with tools: <tool_a>, <tool_b>, ...
Remove route /mcp/<name>
Add tool <tool_name> to route /mcp/<name>
Remove tool <tool_name> from route /mcp/<name>
```

For each instruction, apply exactly these changes and no others:

**Add route** → add a new list to `roles.py`; add `build_mcp(...)` call and export to `server.py`; add import, wrapped app, `_MCP_APPS` entry, and routing branch to `asgi.py`.

**Remove route** → reverse of the above: remove the list from `roles.py`, the instance from `server.py`, and all four touch-points from `asgi.py`.

**Add/remove tool** → edit only the relevant list in `roles.py`. If the tool function is not yet imported at the top of `roles.py`, add the import. If removing a tool leaves an import unused, remove that import too.

---

## Example

> Add route `/mcp/catalog` with tools: `list_departments`, `list_payers`

**`roles.py`** — add import (if not already present) and list:
```python
from .tools.catalog import list_departments, list_payers

CATALOG_TOOLS = [
    list_departments,
    list_payers,
]
```

**`server.py`** — add import and instance:
```python
from .roles import ..., CATALOG_TOOLS

catalog_mcp = build_mcp("MyApp-Catalog", CATALOG_TOOLS)
```

**`asgi.py`** — four additions:
```python
# 1. import
from mcp_server.server import ..., catalog_mcp

# 2. wrapped app
catalog_app = PatientAuthMiddleware(catalog_mcp.streamable_http_app())

# 3. _MCP_APPS (append to existing list)
_MCP_APPS = [..., catalog_app]

# 4. routing branch inside application()
elif path.startswith("/mcp/catalog"):
    await catalog_app(_rewrite_path(scope, "/mcp/catalog"), receive, send)
```

