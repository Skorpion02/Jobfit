# src/utils/url_safety.py
"""
Validación de URLs para mitigar SSRF en el scraper de ofertas.

Reglas que aplica:
- Esquema http/https únicamente
- Dominio dentro de la allowlist de portales de empleo soportados
- Tras resolución DNS, rechaza IPs privadas/loopback/link-local/reservadas
- Permite parametrizar el límite de tamaño de respuesta
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable, Optional
from urllib.parse import urlparse

# Portales de empleo soportados por el scraper genérico + LinkedIn.
# Subdominios se aceptan automáticamente (p. ej. es.linkedin.com).
DEFAULT_ALLOWED_DOMAINS = frozenset({
    "linkedin.com",
    "indeed.com",
    "infojobs.net",
    "jobatus.es",
    "jobatus.com",
    "tecnoempleo.com",
    "glassdoor.com",
    "glassdoor.es",
    "ticjob.es",
    "manfred.com",
})

# Tamaño máximo de respuesta del scraper en bytes (5 MB).
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class URLValidationError(ValueError):
    """Lanzada cuando una URL no pasa los controles de SSRF."""


def _host_matches_allowlist(host: str, allowlist: Iterable[str]) -> bool:
    host = host.lower().strip(".")
    for allowed in allowlist:
        allowed = allowed.lower()
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def _ip_is_unsafe(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_job_url(
    url: str,
    allowlist: Optional[Iterable[str]] = None,
) -> str:
    """
    Valida que `url` sea segura para ser fetcheada por el scraper.

    Devuelve la URL normalizada si pasa. Lanza URLValidationError si no.
    """
    if not isinstance(url, str) or not url.strip():
        raise URLValidationError("URL vacía")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise URLValidationError(
            f"Esquema no permitido: {parsed.scheme or '<vacío>'}. Usa http(s)."
        )

    host = parsed.hostname
    if not host:
        raise URLValidationError("La URL no tiene host")

    domains = allowlist if allowlist is not None else DEFAULT_ALLOWED_DOMAINS
    if not _host_matches_allowlist(host, domains):
        raise URLValidationError(
            f"Dominio no permitido: {host}. "
            f"Allowlist: {sorted(domains)}"
        )

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise URLValidationError(f"DNS falló para {host}: {exc}") from exc

    for info in infos:
        ip = info[4][0]
        if _ip_is_unsafe(ip):
            raise URLValidationError(
                f"El host {host} resuelve a una IP no segura: {ip}"
            )

    return url


def read_capped(response, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
    """
    Lee el body de una respuesta `requests` con `stream=True` cortando
    a `max_bytes` para evitar DoS de memoria.
    """
    buf = bytearray()
    for chunk in response.iter_content(chunk_size=16 * 1024):
        if not chunk:
            continue
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise URLValidationError(
                f"Respuesta excede {max_bytes} bytes — corte por seguridad"
            )
    return bytes(buf)


def safe_get(
    session,
    url: str,
    *,
    max_redirects: int = 3,
    max_bytes: int = MAX_RESPONSE_BYTES,
    allowlist: Optional[Iterable[str]] = None,
    **kwargs,
):
    """
    GET con redirects controlados: revalida cada salto con validate_job_url
    para impedir que un dominio permitido redirija a un host interno.

    Devuelve la última `requests.Response`. Body debe leerse con read_capped.
    """
    import requests

    current = validate_job_url(url, allowlist=allowlist)
    kwargs.setdefault("stream", True)
    kwargs["allow_redirects"] = False

    for _ in range(max_redirects + 1):
        response = session.get(current, **kwargs)
        if response.status_code in (301, 302, 303, 307, 308):
            next_url = response.headers.get("Location")
            response.close()
            if not next_url:
                raise URLValidationError("Redirect sin cabecera Location")
            # URL relativa → resolver contra la base
            if next_url.startswith("/"):
                from urllib.parse import urlparse, urlunparse
                base = urlparse(current)
                next_url = urlunparse((base.scheme, base.netloc, next_url, "", "", ""))
            current = validate_job_url(next_url, allowlist=allowlist)
            continue
        return response

    raise URLValidationError(f"Demasiados redirects (>{max_redirects})")
