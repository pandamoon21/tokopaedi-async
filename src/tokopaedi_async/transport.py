"""Shared GraphQL transport for Tokopedia's internal API.

One deep module owns everything about talking to ``gql.tokopedia.com``:
the endpoint, the iOS-app headers, the device fingerprint, the session
lifecycle, and the timeout/retry policy. The three scrapers
(:mod:`search`, :mod:`get_product`, :mod:`get_reviews`) only build a
payload and hand it here.

The module is deliberately free of import-time side effects so it is safe
to import on a serverless worker (Vercel, AWS Lambda, Cloud Run) where the
import happens once per cold start.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession

from .get_fingerprint import randomize_fp

logger = logging.getLogger(__name__)

GQL_ENDPOINT = "https://gql.tokopedia.com/graphql/{operation}"

# Default request budget. Serverless platforms kill the invocation, not the
# socket, so a per-request timeout is the only thing that stops a hung read
# from eating the whole function's time allowance.
DEFAULT_TIMEOUT = 20.0

# Tokopedia's app asks for identity/device headers on every GraphQL call.
# Two call shapes need slightly different sets, so they are named here once.
_COMMON_HEADERS = {
    "Host": "gql.tokopedia.com",
    "X-Device": "ios-2.318.0",
    "Request-Method": "POST",
    "X-Method": "POST",
    "Accept-Language": "id;q=1.0, en;q=0.9",
    "Content-Type": "application/json; encoding=utf-8",
    "User-Agent": "Tokopedia/2.318.0 (com.tokopedia.Tokopedia; build:202505022018; iOS 18.5.0) Alamofire/2.318.0",
    "X-App-Version": "2.318.0",
    "Accept": "application/json",
    "X-Theme": "default",
    "X-Price-Center": "true",
}


def build_headers(operation: str, dark_mode: bool = False, device: str = "iphone") -> Dict[str, str]:
    """Build the header set for one GraphQL operation.

    A fresh fingerprint is minted per call so repeated requests from the same
    worker do not share a stable device identity.
    """
    user_id, fingerprint = randomize_fp()
    headers = dict(_COMMON_HEADERS)
    headers["X-Tkpd-Path"] = f"/graphql/{operation}"
    headers["Fingerprint-Data"] = fingerprint
    headers["X-Tkpd-Userid"] = user_id
    headers["X-Dark-Mode"] = "true" if dark_mode else "false"
    if device:
        headers["Device-Type"] = device
    return headers


async def post_graphql(
    operation: str,
    payload: Dict[str, Any],
    session: Optional[AsyncSession] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """POST ``payload`` to a Tokopedia GraphQL operation and return the JSON body.

    Args:
        operation: GraphQL operation id, e.g. ``"SearchResult/getProductResult"``.
        payload: The full request body (``query`` + ``variables``).
        session: Optional caller-owned :class:`AsyncSession`. When omitted a
            session is created and closed for this single request, which is the
            correct behaviour under serverless concurrency. Pass a shared
            session only from long-lived processes.
        timeout: Per-request timeout in seconds.

    Returns:
        The decoded JSON body, or ``None`` when the request failed. Errors are
        logged rather than raised so a single failed page does not abort a
        bulk scrape. Callers that need to distinguish failure from an empty
        result can compare against ``None``.

    The return type is the interface: callers never see ``AsyncSession``,
    headers, fingerprints, or the endpoint.
    """
    url = GQL_ENDPOINT.format(operation=operation)
    headers = build_headers(operation)

    owned = session is None
    client = session or AsyncSession()
    try:
        response = await client.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - transport failure is per-request, not fatal
        logger.warning("GraphQL %s failed: %s", operation, exc)
        return None
    finally:
        if owned:
            try:
                await client.close()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
