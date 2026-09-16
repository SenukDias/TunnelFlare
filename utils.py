import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()

def check_cloudflared_installed() -> bool:
    """Check if cloudflared is installed and available in PATH."""
    return shutil.which("cloudflared") is not None

import platform

def get_system_architecture() -> str:
    """Detect system architecture reliably across Linux distributions."""
    machine = platform.machine().lower()
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "armhf",
        "armv6l": "armhf",
        "i386": "386",
        "i686": "386",
    }
    if machine in arch_map:
        return arch_map[machine]
    try:
        return subprocess.check_output(["dpkg", "--print-architecture"]).decode().strip()
    except Exception:
        return machine

def install_cloudflared() -> bool:
    """
    Attempt to install cloudflared on Linux.
    Returns True if successful, False otherwise.
    """
    system = sys.platform
    if system != "linux":
        console.print("[red]Auto-installation is only supported on Linux.[/red]")
        return False

    try:
        # Detect architecture
        arch = get_system_architecture()
        
        url = ""
        if arch == "amd64":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
        elif arch == "arm64":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb"
        elif arch == "armhf":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-armhf.deb"
        elif arch == "386":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386.deb"
        else:
            console.print(f"[red]Unsupported architecture: {arch}[/red]")
            return False

        console.print(f"[cyan]Downloading cloudflared for {arch}...[/cyan]")
        subprocess.run(["wget", "-O", "cloudflared.deb", url], check=True)
        
        console.print("[cyan]Installing cloudflared...[/cyan]")
        subprocess.run(["sudo", "dpkg", "-i", "cloudflared.deb"], check=True)
        
        # Cleanup
        Path("cloudflared.deb").unlink(missing_ok=True)
        
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Installation failed: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")
        return False

def run_command(command: list[str], check: bool = True, capture_output: bool = True) -> Optional[str]:
    """Run a shell command and return its output."""
    try:
        if capture_output:
            result = subprocess.run(
                command, 
                check=check, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(command, check=check)
            return None
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed: {' '.join(command)}[/red]")
        if capture_output:
            console.print(f"[red]Error: {e.stderr}[/red]")
        if check:
            raise e
        return None


import json
import re
import requests


def get_active_interfaces() -> list[dict]:
    """
    Discover local network interfaces, physical MAC addresses, state,
    and assigned IPv4 addresses / CIDRs.
    """
    interfaces = []
    # Try ip -j addr show first
    try:
        raw = subprocess.check_output(["ip", "-j", "addr", "show"], text=True, timeout=3)
        data = json.loads(raw)
        for iface in data:
            name = iface.get("ifname", "")
            if name == "lo":
                continue
            mac = iface.get("address", "")
            operstate = iface.get("operstate", "UNKNOWN").upper()
            ipv4_list = []
            for addr in iface.get("addr_info", []):
                if addr.get("family") == "inet":
                    ip_addr = addr.get("local")
                    prefix = addr.get("prefixlen", 24)
                    ipv4_list.append(f"{ip_addr}/{prefix}")
            
            # Check if this interface has carrier or up
            is_up = operstate in ("UP", "UNKNOWN") and len(ipv4_list) > 0
            interfaces.append({
                "name": name,
                "mac": mac,
                "state": operstate,
                "is_up": is_up,
                "ipv4": ipv4_list,
                "primary_ip": ipv4_list[0] if ipv4_list else None,
            })
        if interfaces:
            return interfaces
    except Exception:
        pass

    # Fallback to /sys/class/net inspection
    net_path = Path("/sys/class/net")
    if net_path.exists():
        for iface_dir in net_path.iterdir():
            name = iface_dir.name
            if name == "lo":
                continue
            mac_file = iface_dir / "address"
            oper_file = iface_dir / "operstate"
            mac = mac_file.read_text().strip() if mac_file.exists() else "00:00:00:00:00:00"
            state = oper_file.read_text().strip().upper() if oper_file.exists() else "UNKNOWN"
            interfaces.append({
                "name": name,
                "mac": mac,
                "state": state,
                "is_up": state == "UP",
                "ipv4": [],
                "primary_ip": None,
            })
    return interfaces


def get_public_ip_and_location() -> dict:
    """
    Query Cloudflare trace and IP geolocation APIs for WAN IP, ISP,
    Cloudflare PoP colocation airport code, and geographic coordinates.
    """
    result = {
        "ip": "Unknown",
        "colo": "Unknown",
        "isp": "Cloudflare Edge",
        "city": "Unknown",
        "country": "Unknown",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    
    # 1. Cloudflare Trace
    try:
        trace = requests.get("https://1.1.1.1/cdn-cgi/trace", timeout=3).text
        for line in trace.splitlines():
            if line.startswith("ip="):
                result["ip"] = line.split("=", 1)[1]
            elif line.startswith("colo="):
                result["colo"] = line.split("=", 1)[1]
            elif line.startswith("loc="):
                result["country"] = line.split("=", 1)[1]
    except Exception:
        pass

    # 2. Geolocation lookup for coordinates
    try:
        geo = requests.get("https://ipapi.co/json/", timeout=3).json()
        if "latitude" in geo and "longitude" in geo:
            result["latitude"] = float(geo.get("latitude", 0.0))
            result["longitude"] = float(geo.get("longitude", 0.0))
            result["city"] = geo.get("city", result["city"])
            result["country"] = geo.get("country_name", result["country"])
            result["isp"] = geo.get("org", result["isp"])
            if result["ip"] == "Unknown":
                result["ip"] = geo.get("ip", "Unknown")
    except Exception:
        pass

    # Country fallback coordinates if latitude/longitude are still 0.0
    if result["latitude"] == 0.0 and result["longitude"] == 0.0:
        country_coords = {
            "LK": (6.9271, 79.8612),    # Sri Lanka / Colombo
            "SG": (1.3521, 103.8198),   # Singapore
            "US": (37.7749, -122.4194), # US / California
            "GB": (51.5074, -0.1278),   # UK / London
            "DE": (50.1109, 8.6821),    # Germany / Frankfurt
            "JP": (35.6762, 139.6503),  # Japan / Tokyo
            "AU": (-33.8688, 151.2093), # Australia / Sydney
            "IN": (19.0760, 72.8777),   # India / Mumbai
            "NL": (52.3676, 4.9041),    # Netherlands / Amsterdam
        }
        loc_code = result.get("country", "").upper()
        if loc_code in country_coords:
            result["latitude"], result["longitude"] = country_coords[loc_code]
            if result["city"] == "Unknown":
                result["city"] = loc_code


    return result


def is_ip_forwarding_enabled() -> bool:
    """Check if IPv4 packet forwarding is enabled in the Linux kernel."""
    forward_file = Path("/proc/sys/net/ipv4/ip_forward")
    if forward_file.exists():
        try:
            return forward_file.read_text().strip() == "1"
        except Exception:
            return False
    return False


def enable_linux_ip_forwarding() -> bool:
    """Enable IPv4 packet forwarding in the Linux kernel for gateway site routing."""
    try:
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        # Try direct write if running with sufficient privileges
        try:
            forward_file = Path("/proc/sys/net/ipv4/ip_forward")
            if forward_file.exists():
                forward_file.write_text("1")
                return True
        except Exception:
            pass
        return False


def configure_iptables_masquerade(interface: str, subnet: str) -> bool:
    """
    Configure iptables MASQUERADE for NAT so remote peers can reach hosts
    behind this gateway.
    """
    try:
        subprocess.run(
            ["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", interface, "-s", subnet, "-j", "MASQUERADE"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False

