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

def run_command(command: list[str], check: bool = True) -> Optional[str]:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command, 
            check=check, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Command failed: {' '.join(command)}[/red]")
        console.print(f"[red]Error: {e.stderr}[/red]")
        if check:
            raise e
        return None
