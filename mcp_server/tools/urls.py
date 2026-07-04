def absolute_view_url(path: str) -> str:
    from django.conf import settings

    base = settings.PUBLIC_BASE_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"
