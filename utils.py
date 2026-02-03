import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from rich.console import Console
import json

console = Console()

def check_cloudflared_installed() -> bool:
    """Check if cloudflared is installed and available in PATH."""
    return shutil.which("cloudflared") is not None

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
        arch = subprocess.check_output(["dpkg", "--print-architecture"]).decode().strip()
        
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

def get_local_cidr() -> Optional[str]:
    """
    Detects the local LAN CIDR (e.g., 192.168.1.0/24).
    Uses 'ip route' on Linux.
    """
    try:
        # Get default interface
        # ip route get 1.1.1.1 -> "1.1.1.1 via ... dev eth0 src 192.168.1.5 ..."
        out = run_command(["ip", "route", "get", "1.1.1.1"], capture_output=True)
        if not out: return None
        
        import re
        # Extract device name
        dev_match = re.search(r"dev\s+(\S+)", out)
        if not dev_match: return None
        interface = dev_match.group(1)
        
        # Get CIDR for that interface
        # ip -o -f inet addr show dev eth0
        addr_out = run_command(["ip", "-o", "-f", "inet", "addr", "show", "dev", interface], capture_output=True)
        if not addr_out: return None
        
        # Match CIDR (e.g., 192.168.1.5/24)
        # Output format: 2: eth0    inet 192.168.1.5/24 brd ...
        cidr_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+/\d+)", addr_out)
        if not cidr_match: return None
        
        full_ip_cidr = cidr_match.group(1)
        
        # Convert IP/Mask to Network/Mask (e.g., 192.168.1.5/24 -> 192.168.1.0/24)
        ip, prefix_str = full_ip_cidr.split('/')
        prefix = int(prefix_str)
        
        parts = [int(p) for p in ip.split('.')]
        ip_int = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]
        
        mask_int = (0xffffffff << (32 - prefix)) & 0xffffffff
        network_int = ip_int & mask_int
        
        net_parts = [
            (network_int >> 24) & 0xff,
            (network_int >> 16) & 0xff,
            (network_int >> 8) & 0xff,
            network_int & 0xff
        ]
        
        return f"{'.'.join(map(str, net_parts))}/{prefix}"
        
    except Exception as e:
        console.print(f"[yellow]Could not detect local CIDR: {e}[/yellow]")
        return None

def add_ip_route(tunnel_id: str, cidr: str) -> bool:
    """Adds a private IP route to the tunnel."""
    # cloudflared tunnel route ip add <cidr> <tunnel_id>
    cmd = ["cloudflared", "tunnel", "route", "ip", "add", cidr, tunnel_id]
    
    try:
        # We handle output manually to check for specific API errors
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
            
        # Check for specific "already exists" error
        if "code: 1014" in result.stderr or "already have a route" in result.stderr:
            console.print(f"[yellow]Route for {cidr} already exists (Code 1014).[/yellow]")
            return True # Treat as success
            
        # Other errors
        console.print(f"[red]Command failed: {' '.join(cmd)}[/red]")
        console.print(f"[red]Error: {result.stderr.strip()}[/red]")
        return False
        
    except Exception as e:
        console.print(f"[red]Execution failed: {e}[/red]")
        return False

def list_ip_routes(tunnel_id: str) -> list[dict]:
    """
    Lists active IP routes for the tunnel.
    Returns a list of dicts: {'network': '10.0.0.0/24', 'tunnel_id': '...', 'vnet': '...'}
    """
    try:
        out = run_command(["cloudflared", "tunnel", "route", "ip", "show", "--output", "json"], capture_output=True)
        if not out: return []
        
        routes = json.loads(out)
        
        tunnel_routes = []
        for r in routes:
            if r.get("tunnel_id") == tunnel_id:
                tunnel_routes.append(r)
                
        return tunnel_routes
    except Exception:
        return []

def get_split_tunnel_json(cidr: str) -> str:
    """Returns the JSON structure for Split Tunnel Include/Exclude."""
    data = {
        "description": "TunnelFlare Route",
        "address": cidr
    }
    return json.dumps(data, indent=2)

