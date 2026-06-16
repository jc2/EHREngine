"""
Cross-Patient Authorization at the MCP boundary (Epic 2.5 / 3, server side)

[Senior Concept: Identity via a trusted channel, not an LLM argument]
A `patient_id` arriving as a tool argument is attacker-controllable (prompt
injection, hallucination). A `patient_id` arriving in the `X-Patient-Id` HTTP
header is set by the harness (the orchestrator) on a trusted channel the LLM
cannot influence. This module captures that trusted identity per request and
lets every tool assert that the patient_id it was asked to operate on matches.

Defense in depth: the harness injects the correct identity AND the MCP validates
it — neither side trusts the LLM for access control.

Mechanics: `PatientAuthMiddleware` is a thin ASGI wrapper that reads the header
into a ContextVar at the start of each request. Tools (which run in a thread via
`sync_to_async`, where the context is copied) read it back via
`enforce_patient_scope`. If no header is present (e.g. a direct/test call), scope
is not enforced — only an explicit, MISMATCHING header is rejected.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_current_patient_id: ContextVar[str | None] = ContextVar(
    "current_patient_id", default=None
)

_HEADER_NAME = b"x-patient-id"


class PatientAuthMiddleware:
    """ASGI middleware that binds the trusted X-Patient-Id header to the request."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        patient_id: str | None = None
        for name, value in scope.get("headers", []):
            if name.lower() == _HEADER_NAME:
                patient_id = value.decode("latin-1").strip() or None
                break

        token = _current_patient_id.set(patient_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_patient_id.reset(token)


def get_authenticated_patient_id() -> str | None:
    """Return the patient_id from the trusted header, or None if unset."""
    return _current_patient_id.get()


def enforce_patient_scope(patient_id: str) -> dict[str, Any] | None:
    """Assert a tool's patient_id argument matches the authenticated identity.

    Returns None when access is allowed (matching header, or no header at all —
    e.g. direct/test invocation). Returns a structured authorization error dict
    when a header is present and the requested patient_id does not match it.
    """
    authenticated = _current_patient_id.get()
    if authenticated is None:
        return None
    if patient_id != authenticated:
        return {
            "success": False,
            "eligible": False,
            "error": (
                "Authorization error: this session is scoped to patient "
                f"'{authenticated}' and may not access data for '{patient_id}'."
            ),
            "error_code": "cross_patient_denied",
        }
    return None
