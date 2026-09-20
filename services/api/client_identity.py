"""Derive rate-limit identities without trusting arbitrary forwarding headers."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from fastapi import Request

from services.api.settings import settings


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer_address = ip_address(peer)
    except ValueError:
        return peer

    trusted = []
    for value in settings.trusted_proxy_cidrs.split(","):
        value = value.strip()
        if value:
            trusted.append(ip_network(value, strict=False))
    if not any(peer_address in network for network in trusted):
        return peer

    forwarded = request.headers.get("x-forwarded-for", "")
    chain = [item.strip() for item in forwarded.split(",") if item.strip()]
    chain.append(peer)
    for item in reversed(chain):
        try:
            address = ip_address(item)
        except ValueError:
            return peer
        if not any(address in network for network in trusted):
            return str(address)
    return peer
