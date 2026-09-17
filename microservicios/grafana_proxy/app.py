"""Proxy local cerrado para embeber un Grafana autenticado en la vista HFC."""

from threading import RLock
from urllib.parse import urljoin, urlsplit

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from microservicios.config import settings

app = FastAPI(title="Grafana Proxy Local", version="1.0.0")

_session = requests.Session()
_session_lock = RLock()
_authenticated = False

_REQUEST_HEADER_DENYLIST = {
    "host",
    "connection",
    "content-length",
    "transfer-encoding",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "upgrade",
    "cookie",
    "authorization",
}
_RESPONSE_HEADER_DENYLIST = {
    "x-frame-options",
    "content-security-policy",
    "content-security-policy-report-only",
    "set-cookie",
    "content-length",
    "transfer-encoding",
    "connection",
}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class ProxyUnavailable(RuntimeError):
    """Indica que el proxy no puede atender la solicitud de forma segura."""


def _configuration_ready() -> bool:
    return bool(
        settings.grafana_proxy_enabled
        and settings.grafana_url.strip()
        and settings.grafana_user
        and settings.grafana_password
    )


def _upstream_base() -> str:
    return settings.grafana_url.rstrip("/") + "/"


def _upstream_origin() -> str:
    parsed = urlsplit(_upstream_base())
    return f"{parsed.scheme}://{parsed.netloc}"


def _login_locked() -> None:
    global _authenticated

    _authenticated = False
    _session.cookies.clear()
    try:
        response = _session.post(
            urljoin(_upstream_base(), "login"),
            json={
                "user": settings.grafana_user,
                "password": settings.grafana_password,
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Backend-Datos-Grafana-Proxy/1.0",
            },
            timeout=settings.grafana_timeout_seconds,
            verify=settings.grafana_verify_ssl,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise ProxyUnavailable("No fue posible autenticar con Grafana") from exc

    if response.status_code < 200 or response.status_code >= 300 or not _session.cookies:
        raise ProxyUnavailable("No fue posible autenticar con Grafana")
    _authenticated = True


def _ensure_authenticated_locked() -> None:
    if not _authenticated:
        _login_locked()


def _request_headers(request: Request) -> dict[str, str]:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _REQUEST_HEADER_DENYLIST
    }
    headers["User-Agent"] = "Backend-Datos-Grafana-Proxy/1.0"
    origin = _upstream_origin()
    if "origin" in request.headers or request.method not in {"GET", "HEAD", "OPTIONS"}:
        headers["Origin"] = origin
    if "referer" in request.headers:
        headers["Referer"] = origin + "/"
    return headers


def _is_login_redirect(response: requests.Response) -> bool:
    if response.status_code not in _REDIRECT_STATUSES:
        return False
    location = response.headers.get("Location", "")
    return urlsplit(urljoin(_upstream_base(), location)).path.startswith("/login")


def _rewrite_location(location: str) -> str:
    resolved = urlsplit(urljoin(_upstream_base(), location))
    upstream = urlsplit(_upstream_base())
    if (resolved.scheme, resolved.netloc) != (upstream.scheme, upstream.netloc):
        raise ProxyUnavailable("Grafana devolvió una redirección no permitida")
    rewritten = resolved.path or "/"
    if resolved.query:
        rewritten += "?" + resolved.query
    if resolved.fragment:
        rewritten += "#" + resolved.fragment
    return rewritten


def _send_upstream(
    request: Request,
    path: str,
    query: str,
    body: bytes,
) -> requests.Response:
    target = _upstream_base() + path.lstrip("/")
    if query:
        target += "?" + query
    return _session.request(
        method=request.method,
        url=target,
        headers=_request_headers(request),
        data=body or None,
        timeout=settings.grafana_timeout_seconds,
        verify=settings.grafana_verify_ssl,
        allow_redirects=False,
    )


def _proxy_locked(
    request: Request,
    path: str,
    query: str,
    body: bytes,
) -> Response:
    global _authenticated

    with _session_lock:
        _ensure_authenticated_locked()
        try:
            upstream = _send_upstream(request, path, query, body)
        except requests.RequestException as exc:
            raise ProxyUnavailable("Grafana no está disponible") from exc

        if upstream.status_code == 401 or _is_login_redirect(upstream):
            _authenticated = False
            _login_locked()
            try:
                upstream = _send_upstream(request, path, query, body)
            except requests.RequestException as exc:
                raise ProxyUnavailable("Grafana no está disponible") from exc
            if upstream.status_code == 401 or _is_login_redirect(upstream):
                _authenticated = False
                raise ProxyUnavailable("La sesión de Grafana no está disponible")

        headers = {
            name: value
            for name, value in upstream.headers.items()
            if name.lower() not in _RESPONSE_HEADER_DENYLIST
        }
        if "Location" in headers:
            headers["Location"] = _rewrite_location(headers["Location"])
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=headers,
        )


@app.get("/__proxy_health")
def proxy_health() -> dict[str, object]:
    return {
        "ok": True,
        "service": "grafana-proxy",
        "enabled": settings.grafana_proxy_enabled,
    }


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy(path: str, request: Request) -> Response:
    if not _configuration_ready():
        return JSONResponse(
            status_code=503 if settings.grafana_proxy_enabled else 404,
            content={"ok": False, "error": "Proxy Grafana no disponible"},
        )

    if path.strip("/").lower() in {"login", "logout"}:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "Ruta no disponible"},
        )

    body = await request.body()
    try:
        return await run_in_threadpool(
            _proxy_locked,
            request,
            path,
            request.url.query,
            body,
        )
    except ProxyUnavailable:
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": "Proxy Grafana no disponible"},
        )
