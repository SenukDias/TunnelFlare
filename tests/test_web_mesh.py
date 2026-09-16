"""
Automated unit and integration tests for TunnelFlare Hybrid Web Mesh.
Tests Cloudflare Zero Trust client, local network discovery, FastAPI endpoints,
and React SPA serving.
"""

from fastapi.testclient import TestClient
import cloudflare_api
import utils
from web_server import app

client = TestClient(app)


def test_network_discovery():
    """Verify hardware interface and MAC address discovery."""
    interfaces = utils.get_active_interfaces()
    assert isinstance(interfaces, list)
    assert len(interfaces) > 0
    for iface in interfaces:
        assert "name" in iface
        assert "mac" in iface
        assert "state" in iface


def test_public_ip_and_location():
    """Verify Cloudflare trace and geo-coordinate resolution."""
    pub = utils.get_public_ip_and_location()
    assert isinstance(pub, dict)
    assert "ip" in pub
    assert "latitude" in pub
    assert "longitude" in pub


def test_status_endpoint():
    """Verify GET /api/v1/status returns node identity and network info."""
    res = client.get("/api/v1/status")
    assert res.status_code == 200
    data = res.json()
    assert "site_name" in data
    assert "public_ip" in data
    assert "colo" in data
    assert "interfaces" in data


def test_mesh_nodes_endpoint():
    """Verify GET /api/v1/mesh/nodes returns local gateway and mesh topology."""
    res = client.get("/api/v1/mesh/nodes")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert len(data["nodes"]) >= 1
    local_node = data["nodes"][0]
    assert "lan_cidr" in local_node
    assert "mac" in local_node


def test_static_spa_serving():
    """Verify GET / serves the compiled React application."""
    res = client.get("/")
    assert res.status_code == 200
    assert "TunnelFlare" in res.text
    assert "index-" in res.text or "assets" in res.text
