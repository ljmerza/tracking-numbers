"""Carrier-direct (free) tracking clients: USPS, UPS, FedEx, DHL.

Optional: used only when the status provider is set to "carriers" and the
relevant carrier credentials are configured. Every client returns the same
normalized dict as the TrackingMore client — {status, delivery_status,
estimated_delivery} — or None on failure (logged, never raised into the
coordinator's update loop). See const.py for endpoints and status maps.

USPS/UPS/FedEx authenticate with OAuth2 client-credentials (tokens cached and
refreshed on expiry or a 401); DHL uses a simple API-key header.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from typing import Any

import aiohttp

from .const import (
    CARRIER_STATUS_LABELS,
    CARRIER_TIMEOUT,
    CONF_DHL_API_KEY,
    CONF_FEDEX_CLIENT_ID,
    CONF_FEDEX_CLIENT_SECRET,
    CONF_UPS_CLIENT_ID,
    CONF_UPS_CLIENT_SECRET,
    CONF_USPS_CLIENT_ID,
    CONF_USPS_CLIENT_SECRET,
    DHL_STATUS_MAP,
    DHL_TRACK_URL,
    FEDEX_STATUS_MAP,
    FEDEX_TOKEN_URL,
    FEDEX_TRACK_URL,
    UPS_STATUS_MAP,
    UPS_TOKEN_URL,
    UPS_TRACK_URL,
    USPS_STATUS_MAP,
    USPS_TOKEN_URL,
    USPS_TRACK_URL,
)

_LOGGER = logging.getLogger(__name__)

TRANSACTION_SRC = "ha-tracking-numbers"


def _result(delivery_status: str, eta: str | None = None) -> dict[str, Any]:
    """Build the normalized status dict written onto a package.

    `delivery_status` is the normalized enum (delivered / out_for_delivery /
    transit / pending / exception / notfound); the card colors its chip from it.
    """
    label = CARRIER_STATUS_LABELS.get(delivery_status)
    return {
        "delivery_status": delivery_status,
        "status": label or (delivery_status.replace("_", " ").title() if delivery_status else None),
        "estimated_delivery": eta,
    }


def _date_only(value: Any) -> str | None:
    """Reduce an ISO datetime string to its date part (YYYY-MM-DD)."""
    if not value or not isinstance(value, str):
        return None
    return value.split("T", 1)[0]


def _ups_date(value: Any) -> str | None:
    """Convert UPS's YYYYMMDD to YYYY-MM-DD."""
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


async def _request(
    session: aiohttp.ClientSession, method: str, url: str, **kwargs: Any
) -> tuple[int | None, Any]:
    """Perform a request; return (http_status, parsed_json) or (None, None)."""
    try:
        async with session.request(
            method, url, timeout=aiohttp.ClientTimeout(total=CARRIER_TIMEOUT), **kwargs
        ) as resp:
            try:
                body = await resp.json(content_type=None)
            except Exception:  # pylint: disable=broad-except
                body = None
            return resp.status, body
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.warning("Carrier request failed %s %s: %s", method, url, err)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning("Unexpected carrier error %s %s: %s", method, url, err)
    return None, None


class _OAuthCarrierClient:
    """Base for OAuth2 client-credentials carriers with token caching."""

    code = ""
    token_ttl_fallback = 3600  # seconds; overridden per carrier

    def __init__(
        self, session: aiohttp.ClientSession, client_id: str, client_secret: str
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expiry = 0.0

    async def _fetch_token(self) -> dict[str, Any] | None:
        raise NotImplementedError

    async def _get_token(self, force: bool = False) -> str | None:
        if not force and self._token and time.monotonic() < self._token_expiry:
            return self._token
        data = await self._fetch_token()
        token = (data or {}).get("access_token")
        if not token:
            _LOGGER.warning("%s: could not obtain OAuth token", self.code)
            self._token = None
            return None
        try:
            ttl = int(data.get("expires_in") or self.token_ttl_fallback)
        except (TypeError, ValueError):
            ttl = self.token_ttl_fallback
        self._token = token
        # Refresh a minute early to avoid using a just-expired token.
        self._token_expiry = time.monotonic() + max(60, ttl - 60)
        return token

    async def _authed_request(
        self, method: str, url: str, **kwargs: Any
    ) -> tuple[int | None, Any]:
        token = await self._get_token()
        if not token:
            return None, None
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        status, body = await _request(self._session, method, url, headers=headers, **kwargs)
        if status == 401:  # token may be stale; refresh once and retry
            token = await self._get_token(force=True)
            if not token:
                return None, None
            headers["Authorization"] = f"Bearer {token}"
            status, body = await _request(self._session, method, url, headers=headers, **kwargs)
        return status, body


class UspsClient(_OAuthCarrierClient):
    code = "usps"
    token_ttl_fallback = 28800  # ~8h

    async def _fetch_token(self) -> dict[str, Any] | None:
        _, body = await _request(
            self._session,
            "POST",
            USPS_TOKEN_URL,
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
                "scope": "tracking",
            },
        )
        return body

    async def track(self, tracking_number: str) -> dict[str, Any] | None:
        status, body = await self._authed_request(
            "GET",
            USPS_TRACK_URL.format(number=tracking_number),
            params={"expand": "DETAIL"},
        )
        if status == 404:
            return _result("notfound")
        if not isinstance(body, dict):
            return None
        cat = (body.get("statusCategory") or "").strip().lower()
        ds = USPS_STATUS_MAP.get(cat, "transit")
        # NOTE: the estimated-delivery field name is unverified in USPS's v3 docs;
        # try the likely candidates and fall back to None.
        eta = (
            body.get("expectedDeliveryDate")
            or body.get("expectedDeliveryTimeStamp")
            or body.get("guaranteedDeliveryDate")
        )
        return _result(ds, _date_only(eta))


class UpsClient(_OAuthCarrierClient):
    code = "ups"
    token_ttl_fallback = 3600  # ~1h since 2026-04-01

    async def _fetch_token(self) -> dict[str, Any] | None:
        basic = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()
        _, body = await _request(
            self._session,
            "POST",
            UPS_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {basic}"},
        )
        return body

    async def track(self, tracking_number: str) -> dict[str, Any] | None:
        status, body = await self._authed_request(
            "GET",
            UPS_TRACK_URL.format(number=tracking_number),
            headers={"transId": uuid.uuid4().hex, "transactionSrc": TRANSACTION_SRC},
        )
        if not isinstance(body, dict):
            return None
        try:
            pkg = body["trackResponse"]["shipment"][0]["package"][0]
        except (KeyError, IndexError, TypeError):
            return None
        cs = pkg.get("currentStatus") or {}
        status_type = (cs.get("type") or "").upper()
        desc = (cs.get("description") or cs.get("simplifiedTextDescription") or "").lower()
        ds = UPS_STATUS_MAP.get(status_type, "transit")
        if status_type == "D" and "out for delivery" in desc:
            ds = "out_for_delivery"
        eta = None
        for entry in pkg.get("deliveryDate") or []:
            if entry.get("type") in ("SDD", "RDD"):
                eta = _ups_date(entry.get("date"))
                break
        return _result(ds, eta)


class FedexClient(_OAuthCarrierClient):
    code = "fedex"
    token_ttl_fallback = 3600  # ~1h

    async def _fetch_token(self) -> dict[str, Any] | None:
        _, body = await _request(
            self._session,
            "POST",
            FEDEX_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        return body

    async def track(self, tracking_number: str) -> dict[str, Any] | None:
        _, body = await self._authed_request(
            "POST",
            FEDEX_TRACK_URL,
            json={
                "includeDetailedScans": False,
                "trackingInfo": [
                    {"trackingNumberInfo": {"trackingNumber": tracking_number}}
                ],
            },
            headers={"X-locale": "en_US", "Content-Type": "application/json"},
        )
        if not isinstance(body, dict):
            return None
        try:
            tr = body["output"]["completeTrackResults"][0]["trackResults"][0]
        except (KeyError, IndexError, TypeError):
            return None
        if tr.get("error"):  # per-number error comes back inside an HTTP 200
            return _result("notfound")
        lsd = tr.get("latestStatusDetail") or {}
        code = (lsd.get("derivedCode") or lsd.get("code") or "").upper()
        ds = FEDEX_STATUS_MAP.get(code, "transit")
        eta = None
        for entry in tr.get("dateAndTimes") or []:
            if entry.get("type") == "ESTIMATED_DELIVERY":
                eta = _date_only(entry.get("dateTime"))
                break
        return _result(ds, eta)


class DhlClient:
    code = "dhl"

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        self._session = session
        self._api_key = api_key

    async def track(self, tracking_number: str) -> dict[str, Any] | None:
        status, body = await _request(
            self._session,
            "GET",
            DHL_TRACK_URL,
            params={"trackingNumber": tracking_number},
            headers={"DHL-API-Key": self._api_key},
        )
        if status == 404:
            return _result("notfound")
        if not isinstance(body, dict):
            return None
        shipments = body.get("shipments") or []
        if not shipments:
            return _result("notfound")
        shipment = shipments[0]
        code = ((shipment.get("status") or {}).get("statusCode") or "").strip().lower()
        ds = DHL_STATUS_MAP.get(code, "transit")
        eta = _date_only(shipment.get("estimatedTimeOfDelivery"))
        return _result(ds, eta)


def build_carrier_clients(
    session: aiohttp.ClientSession, options: dict[str, Any]
) -> dict[str, Any]:
    """Return {carrier_code: client} for carriers that have credentials set."""
    clients: dict[str, Any] = {}

    usps_id = options.get(CONF_USPS_CLIENT_ID)
    usps_secret = options.get(CONF_USPS_CLIENT_SECRET)
    if usps_id and usps_secret:
        clients["usps"] = UspsClient(session, usps_id, usps_secret)

    ups_id = options.get(CONF_UPS_CLIENT_ID)
    ups_secret = options.get(CONF_UPS_CLIENT_SECRET)
    if ups_id and ups_secret:
        clients["ups"] = UpsClient(session, ups_id, ups_secret)

    fedex_id = options.get(CONF_FEDEX_CLIENT_ID)
    fedex_secret = options.get(CONF_FEDEX_CLIENT_SECRET)
    if fedex_id and fedex_secret:
        clients["fedex"] = FedexClient(session, fedex_id, fedex_secret)

    dhl_key = options.get(CONF_DHL_API_KEY)
    if dhl_key:
        clients["dhl"] = DhlClient(session, dhl_key)

    return clients
