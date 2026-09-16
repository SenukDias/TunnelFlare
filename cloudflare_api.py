"""
Cloudflare Zero Trust API Client for TunnelFlare.
Orchestrates Cloudflare v4 REST API operations: Account verification,
Tunnel discovery, Virtual Networks (Teamnet VNets), and CIDR Mesh Routing.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

CONFIG_DIR = Path.home() / ".tunnelflare"
ACCOUNT_FILE = CONFIG_DIR / "account.json"
BASE_URL = "https://api.cloudflare.com/client/v4"


class CloudflareAPIError(Exception):
    """Exception raised for errors in the Cloudflare API response."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.errors = errors or []
        self.status_code = status_code


class CloudflareClient:
    """Client for Cloudflare Zero Trust v4 REST API."""

    def __init__(self, token: Optional[str] = None, account_id: Optional[str] = None):
        self.token = token
        self.account_id = account_id

    def _headers(self, override_token: Optional[str] = None) -> Dict[str, str]:
        tok = override_token or self.token
        if not tok:
            raise CloudflareAPIError("Cloudflare API token is required but not provided.")
        return {
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "User-Agent": "TunnelFlare-Mesh/2.0",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
    ) -> Dict[str, Any]:
        url = f"{BASE_URL}{endpoint}"
        headers = self._headers(token)
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout,
            )
            data = resp.json()
        except requests.RequestException as e:
            raise CloudflareAPIError(f"Network error connecting to Cloudflare API: {e}")
        except json.JSONDecodeError:
            raise CloudflareAPIError(f"Invalid JSON response from Cloudflare API (HTTP {resp.status_code})", status_code=resp.status_code)

        if not data.get("success", False):
            errors = data.get("errors", [])
            messages = data.get("messages", [])
            err_msg = "; ".join([e.get("message", str(e)) for e in errors]) or "; ".join(messages) or f"Request failed with HTTP {resp.status_code}"
            raise CloudflareAPIError(err_msg, errors=errors, status_code=resp.status_code)

        return data.get("result", {})

    # ---------------------------------------------------------
    # Authentication & Account Discovery
    # ---------------------------------------------------------
    def verify_token(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Verify the validity and permissions of an API token."""
        return self._request("GET", "/user/tokens/verify", token=token)

    def get_accounts(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all accounts accessible with this API token."""
        result = self._request("GET", "/accounts", token=token)
        if isinstance(result, list):
            return result
        return []

    # ---------------------------------------------------------
    # Cloudflare Tunnels (cfd_tunnel)
    # ---------------------------------------------------------
    def list_tunnels(self, account_id: Optional[str] = None, token: Optional[str] = None, is_deleted: bool = False) -> List[Dict[str, Any]]:
        """List Cloudflare tunnels in the given account."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to list tunnels.")
        params = {"is_deleted": str(is_deleted).lower()}
        result = self._request("GET", f"/accounts/{acc_id}/cfd_tunnel", token=token, params=params)
        return result if isinstance(result, list) else []

    def get_tunnel(self, tunnel_id: str, account_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve details of a specific tunnel."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to get tunnel details.")
        return self._request("GET", f"/accounts/{acc_id}/cfd_tunnel/{tunnel_id}", token=token)

    def get_tunnel_token(self, tunnel_id: str, account_id: Optional[str] = None, token: Optional[str] = None) -> str:
        """Fetch the base64 tunnel connector token for headless agent run."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to fetch tunnel token.")
        result = self._request("GET", f"/accounts/{acc_id}/cfd_tunnel/{tunnel_id}/token", token=token)
        if isinstance(result, str):
            return result
        return result.get("token", "") if isinstance(result, dict) else str(result)

    def create_tunnel(self, name: str, account_id: Optional[str] = None, token: Optional[str] = None, config_src: str = "cloudflare") -> Dict[str, Any]:
        """Create a new Cloudflare Tunnel in the account."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to create a tunnel.")
        payload = {"name": name, "config_src": config_src}
        return self._request("POST", f"/accounts/{acc_id}/cfd_tunnel", token=token, json_data=payload)

    def delete_tunnel(self, tunnel_id: str, account_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """Delete an existing tunnel."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to delete a tunnel.")
        return self._request("DELETE", f"/accounts/{acc_id}/cfd_tunnel/{tunnel_id}", token=token)

    # ---------------------------------------------------------
    # Virtual Networks (Teamnet VNets)
    # ---------------------------------------------------------
    def list_virtual_networks(self, account_id: Optional[str] = None, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Virtual Networks configured in Cloudflare Zero Trust."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to list virtual networks.")
        result = self._request("GET", f"/accounts/{acc_id}/teamnet/virtual_networks", token=token)
        return result if isinstance(result, list) else []

    def create_virtual_network(
        self,
        name: str,
        is_default: bool = False,
        comment: str = "Created by TunnelFlare Mesh",
        account_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Virtual Network for isolated site-to-site mesh routing."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to create a virtual network.")
        payload = {"name": name, "is_default_network": is_default, "comment": comment}
        return self._request("POST", f"/accounts/{acc_id}/teamnet/virtual_networks", token=token, json_data=payload)

    # ---------------------------------------------------------
    # Teamnet CIDR Routes (Private Site-to-Site Mesh)
    # ---------------------------------------------------------
    def list_routes(
        self,
        account_id: Optional[str] = None,
        token: Optional[str] = None,
        is_deleted: bool = False,
        network: Optional[str] = None,
        tunnel_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all active CIDR routes in Cloudflare Zero Trust."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to list routes.")
        params: Dict[str, Any] = {"is_deleted": str(is_deleted).lower()}
        if network:
            params["network"] = network
        if tunnel_id:
            params["tunnel_id"] = tunnel_id
        result = self._request("GET", f"/accounts/{acc_id}/teamnet/routes", token=token, params=params)
        return result if isinstance(result, list) else []

    def add_cidr_route(
        self,
        network: str,
        tunnel_id: str,
        comment: str = "TunnelFlare Mesh Route",
        virtual_network_id: Optional[str] = None,
        account_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a private CIDR subnet (e.g. 192.168.10.0/24) to route through a tunnel.
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to add a route.")
        payload: Dict[str, Any] = {
            "network": network,
            "tunnel_id": tunnel_id,
            "comment": comment,
        }
        if virtual_network_id:
            payload["virtual_network_id"] = virtual_network_id
        return self._request("POST", f"/accounts/{acc_id}/teamnet/routes", token=token, json_data=payload)

    def delete_cidr_route(self, route_id: str, account_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, Any]:
        """Revoke a registered CIDR route."""
        acc_id = account_id or self.account_id
        if not acc_id:
            raise CloudflareAPIError("Account ID is required to delete a route.")
        return self._request("DELETE", f"/accounts/{acc_id}/teamnet/routes/{route_id}", token=token)


# -------------------------------------------------------------
# Local Account Configuration Helpers
# -------------------------------------------------------------
def save_account_config(
    token: str,
    account_id: str,
    account_name: str = "",
    site_name: str = "",
    default_vnet_id: Optional[str] = None,
) -> None:
    """Save Cloudflare Zero Trust account configuration securely with 0600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = ACCOUNT_FILE.with_suffix(".tmp")
    data = {
        "token": token,
        "account_id": account_id,
        "account_name": account_name,
        "site_name": site_name,
        "default_vnet_id": default_vnet_id,
    }
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.chmod(temp_file, 0o600)
    os.replace(temp_file, ACCOUNT_FILE)


def load_account_config() -> Optional[Dict[str, Any]]:
    """Load the saved Cloudflare Zero Trust account configuration."""
    if not ACCOUNT_FILE.exists():
        return None
    try:
        with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_account_config() -> None:
    """Remove the saved account configuration."""
    if ACCOUNT_FILE.exists():
        ACCOUNT_FILE.unlink(missing_ok=True)
