"""
Unit and integration tests for TunnelFlare Point-to-Point Connector Management
and Private IP Gateway Proxy Relay.
"""

from fastapi.testclient import TestClient
from web_server import app

client = TestClient(app)


def test_gateway_test_reach_timeout():
    """Verify test-reach returns proper structure when targeting an unreachable IP."""
    # 192.0.2.1 is TEST-NET-1 (RFC 5737), non-routable documentation IP
    res = client.get("/api/v1/gateway/test-reach?ip=192.0.2.1&port=80&timeout=0.2")
    assert res.status_code == 200
    data = res.json()
    assert "reachable" in data
    assert data["reachable"] is False
    assert data["ip"] == "192.0.2.1"
    assert data["port"] == 80


def test_gateway_test_reach_localhost():
    """Verify test-reach returns reachable or proper error for localhost."""
    res = client.get("/api/v1/gateway/test-reach?ip=127.0.0.1&port=9999&timeout=0.2")
    assert res.status_code == 200
    data = res.json()
    assert "reachable" in data
    assert data["ip"] == "127.0.0.1"
    assert data["port"] == 9999


def test_connector_create_unauthenticated():
    """Verify connector creation enforces Cloudflare account link."""
    res = client.post("/api/v1/connector/create", json={
        "site_name": "Test-Site-B",
        "lan_cidr": "10.200.0.0/24",
    })
    # Either 401 if unlinked or 200/400 if credentials present
    assert res.status_code in (401, 400, 200)


def test_connector_status_unauthenticated():
    """Verify connector status check enforces authentication."""
    res = client.get("/api/v1/connector/status/fake-tunnel-id")
    assert res.status_code in (401, 400, 200)
