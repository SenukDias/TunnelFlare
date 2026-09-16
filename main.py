import typer
import time
import random
import subprocess
import os
import signal
import sys
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.tree import Tree
from pathlib import Path
import socket
import requests
import yaml
from typing import Optional, List, Dict, Any
from rich import box

from utils import check_cloudflared_installed, install_cloudflared, run_command

app = typer.Typer()
console = Console()

CLOUDFLARE_ORANGE = "#F38020"
CYBER_CYAN = "#00E5FF"
NEON_EMERALD = "#00E676"

TUNNEL_FLARE_LOGO = """
 [bold #F38020]████████╗██╗   ██╗███╗   ██╗███╗   ██╗███████╗██╗     ███████╗██╗      █████╗ ██████╗ ███████╗[/]
 [bold #F38020]╚══██╔══╝██║   ██║████╗  ██║████╗  ██║██╔════╝██║     ██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝[/]
 [bold #F38020]   ██║   ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║     █████╗  ██║     ███████║██████╔╝█████╗  [/]
 [bold #F38020]   ██║   ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║     ██╔══╝  ██║     ██╔══██║██╔══██╗██╔══╝  [/]
 [bold #F38020]   ██║   ╚██████╔╝██║ ╚████║██║ ╚████║███████╗███████╗██║     ███████╗██║  ██║██║  ██║███████╗[/]
 [bold #F38020]   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝[/]
"""

# Compact Logo for smaller screens or just cleaner look
TUNNEL_FLARE_LOGO_COMPACT = """
 [bold #F38020]████████╗██╗   ██╗███╗   ██╗███╗   ██╗███████╗██╗     ███████╗██╗      █████╗ ██████╗ ███████╗[/]
 [bold #F38020]╚══██╔══╝██║   ██║████╗  ██║████╗  ██║██╔════╝██║     ██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝[/]
 [bold #F38020]   ██║   ╚██████╔╝██║ ╚████║██║ ╚████║███████╗███████╗██║     ███████╗██║  ██║██║  ██║███████╗[/]
 [bold #F38020]   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝[/]
"""

STEPS = [
    "Pre-Flight & Deps",
    "Authentication",
    "Create Tunnel",
    "VPN Architecture",
    "Configuration",
    "Run Tunnel"
]

TUNNEL_DIR = Path.home() / ".tunnelflare"
PID_FILE = TUNNEL_DIR / "tunnel.pid"
LOG_FILE = TUNNEL_DIR / "tunnel.log"
CONFIG_FILE = TUNNEL_DIR / "config.yml"

def get_header(current_step_index: int = -1):
    """
    Returns a renderable group containing the Logo and the Step Progress.
    """
    # Logo
    logo_panel = Align.center(Text.from_markup(TUNNEL_FLARE_LOGO_COMPACT))
    
    # Steps
    steps_text = Text()
    for i, step in enumerate(STEPS):
        if i == current_step_index:
            style = f"bold {CLOUDFLARE_ORANGE} reverse"
            prefix = "➤ "
        elif i < current_step_index:
            style = f"bold green"
            prefix = "✓ "
        else:
            style = "dim white"
            prefix = "○ "
            
        steps_text.append(f" {prefix}{step} ", style=style)
        if i < len(STEPS) - 1:
            steps_text.append(" → ", style="dim")
    if current_step_index >= 0:
        steps_panel = Panel(Align.center(steps_text), title="Setup Progress", border_style=CLOUDFLARE_ORANGE)
        return Group(logo_panel, steps_panel)
    return logo_panel


def refresh_interface(current_step_index: int):
    """Clears screen and prints the header."""
    console.clear()
    console.print(get_header(current_step_index))
    console.print("\n")

def start_tunnel_background(tunnel_id: str, config_path: Path, cred_path: Path):
    """
    Starts the tunnel in the background and saves the PID.
    """
    TUNNEL_DIR.mkdir(exist_ok=True)
    
    cmd = [
        "cloudflared", 
        "tunnel", 
        "--config", str(config_path), 
        "--cred-file", str(cred_path),
        "run", 
        tunnel_id
    ]
    
    with open(LOG_FILE, "w") as log:
        process = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True # Detach from terminal
        )
    
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))
        
    console.print(f"[green]Tunnel '{tunnel_id}' started in background (PID: {process.pid}).[/green]")
    console.print(f"Logs are being written to {LOG_FILE}")
    console.print(f"\n[bold]Run [cyan]tunnelflare status[/cyan] to view live status.[/bold]")

def is_tunnel_running():
    """Checks if the tunnel process is running based on the PID file."""
    if not PID_FILE.exists():
        return False
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, OSError):
        return False

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    TunnelFlare: Secure Highway to your Private Server.
    """
    if ctx.invoked_subcommand is None:
        console.print(Align.center(Text.from_markup(TUNNEL_FLARE_LOGO)))
        console.print(Align.center(Text("By. Senuk Dias", style=f"bold {CLOUDFLARE_ORANGE}")))
        console.print("\n")
        console.print(ctx.get_help())

def check_preflight_connectivity() -> bool:
    """Check connectivity to Internet, DNS, and Cloudflare."""
    console.print(f"[{CLOUDFLARE_ORANGE}]Verifying Network Connectivity...[/{CLOUDFLARE_ORANGE}]")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(("1.1.1.1", 53))
        s.close()
        console.print("[green]✓ Internet & DNS reachable (1.1.1.1)[/green]")
    except Exception as e:
        console.print(f"[red]✖ Network connectivity check failed: {e}[/red]")
        if not Confirm.ask("Do you want to continue anyway?", default=False):
            raise typer.Exit(code=1)

    try:
        res = requests.get("https://cloudflare.com/cdn-cgi/trace", timeout=4.0)
        if res.status_code == 200:
            console.print("[green]✓ Cloudflare Global Anycast Edge verified[/green]")
    except Exception:
        console.print("[yellow]! Cloudflare Edge trace timed out, continuing...[/yellow]")
    return True

@app.command()
def setup():
    """
    Interactive setup wizard for Cloudflare Tunnel with VPN Mode Selection.
    """
    step_index = 0
    
    # 1. Pre-Flight & Dependencies
    refresh_interface(step_index)
    check_preflight_connectivity()
    
    if not check_cloudflared_installed():
        console.print("[red]cloudflared is not installed.[/red]")
        if Confirm.ask("Do you want to install it now?"):
            if install_cloudflared():
                console.print("[green]cloudflared installed successfully![/green]")
            else:
                console.print("[red]Failed to install cloudflared. Please try installing manually.[/red]")
                raise typer.Exit(code=1)
        else:
            console.print("[yellow]cloudflared is required to continue. Please install it and run setup again.[/yellow]")
            raise typer.Exit(code=1)
    else:
        console.print("[green]cloudflared is installed and ready.[/green]")
    
    time.sleep(1)
    step_index += 1

    # 2. Authentication (URL-based)
    refresh_interface(step_index)
    cert_path = Path.home() / ".cloudflared" / "cert.pem"
    
    need_login = False
    if not cert_path.exists():
        need_login = True
    else:
        console.print(f"[green]Existing Cloudflare certificate found: {cert_path}[/green]")
        if Confirm.ask("Do you want to re-authenticate with a new domain/account?", default=False):
            need_login = True

    if need_login:
        console.print("\n[bold cyan]Cloudflare URL-Based Authentication[/bold cyan]")
        console.print("A browser window will open to authorize your Cloudflare domain.")
        console.print("[yellow]If the browser does not open automatically, copy and open the URL printed below:[/yellow]\n")
        if Confirm.ask("Ready to authenticate with Cloudflare?", default=True):
            try:
                run_command(["cloudflared", "tunnel", "login"], check=True, capture_output=False)
                if cert_path.exists():
                    console.print("[green]✓ Authentication successful! Certificate written.[/green]")
                else:
                    console.print("[yellow]Certificate file not detected yet. Proceeding with caution.[/yellow]")
            except Exception as e:
                console.print(f"[red]Authentication failed or was cancelled: {e}[/red]")
                raise typer.Exit(code=1)
    else:
        console.print("[green]✓ Using existing authenticated Cloudflare credentials.[/green]")
    
    time.sleep(1)
    step_index += 1

    # 3. Create Tunnel
    refresh_interface(step_index)
    tunnel_name = Prompt.ask("Enter a name for your tunnel", default="my-tunnel")
    
    tunnel_id = None
    try:
        # Attempt to create tunnel
        create_output = run_command(["cloudflared", "tunnel", "create", tunnel_name], check=False)
        
        if create_output and "Tunnel credentials written" in create_output:
             console.print(f"[green]Tunnel '{tunnel_name}' created successfully![/green]")
        
        elif create_output and "already exists" in create_output:
             console.print(f"[yellow]Tunnel '{tunnel_name}' already exists remotely.[/yellow]")
             
             # Get ID to check for local credentials
             tunnels_list = run_command(["cloudflared", "tunnel", "list"], check=True)
             for line in tunnels_list.splitlines():
                if tunnel_name in line:
                    parts = line.split()
                    if len(parts) > 0:
                        tunnel_id = parts[0]
                        break
             
             if tunnel_id:
                 cred_file = Path.home() / ".cloudflared" / f"{tunnel_id}.json"
                 if not cred_file.exists():
                     console.print(f"[red]Local credentials missing for ID {tunnel_id}.[/red]")
                     console.print("[cyan]Deleting old remote tunnel to recreate it...[/cyan]")
                     run_command(["cloudflared", "tunnel", "delete", "-f", tunnel_name], check=False)
                     
                     create_output = run_command(["cloudflared", "tunnel", "create", tunnel_name], check=True)
                     if "Tunnel credentials written" in create_output:
                         console.print(f"[green]Tunnel '{tunnel_name}' recreated successfully![/green]")
                     else:
                         console.print("[red]Failed to recreate tunnel.[/red]")
                         raise typer.Exit(code=1)
                 else:
                     console.print(f"[green]Using existing tunnel '{tunnel_name}' with valid credentials.[/green]")
        
        # Get Tunnel ID (if not already fetched)
        if not tunnel_id:
            tunnels_list = run_command(["cloudflared", "tunnel", "list"], check=True)
            for line in tunnels_list.splitlines():
                if tunnel_name in line:
                    parts = line.split()
                    if len(parts) > 0:
                        tunnel_id = parts[0]
                        break
        
        if not tunnel_id:
            console.print(f"[red]Could not find ID for tunnel '{tunnel_name}'.[/red]")
            raise typer.Exit(code=1)
            
        console.print(f"Tunnel ID: [bold cyan]{tunnel_id}[/bold cyan]")
        
    except Exception as e:
        console.print(f"[red]Error creating tunnel: {e}[/red]")
        console.print("[yellow]Tip: Ensure you are logged in and have permissions to create tunnels.[/yellow]")
        raise typer.Exit(code=1)

    time.sleep(1)
    step_index += 1

    # 4. VPN Architecture & Configuration
    refresh_interface(step_index)
    cred_path = Path.home() / ".cloudflared" / f"{tunnel_id}.json"
    ingress_rules = []
    warp_routing_enabled = False

    console.print(Panel("""[bold #F38020]SELECT TUNNEL / VPN ARCHITECTURE MODE[/]

[bold cyan]1. Server-to-Client Mode (Hosted Web & SSH Services)[/]
   • Exposes local web apps, APIs, and SSH servers to external users.
   • Automatically provisions Cloudflare DNS CNAME records.
   • Ideal for hosting servers, webhooks, dashboards, and remote SSH.

[bold cyan]2. Client-to-Client / Site-to-Site Mode (Private Network CIDR VPN)[/]
   • Connects private subnets (e.g. 192.168.10.0/24 <-> 192.168.20.0/24) via Cloudflare WARP.
   • Operates without open inbound ports using Cloudflare Private Network CIDR routes.
   • Ideal for Site-to-Site VPN mesh, LAN-to-LAN interconnects, and zero-trust intranet.
""", border_style=CLOUDFLARE_ORANGE))

    vpn_mode = Prompt.ask("Choose VPN Architecture Mode", choices=["1", "2"], default="1")

    if vpn_mode == "1":
        # Helper to add service
        def add_service_prompt(default_type="http"):
            while True:
                console.print(f"\n[bold]Add a Service ({default_type.upper()})[/bold]")
                if default_type == "ssh":
                    if not typer.confirm("Do you want to enable SSH access?", default=False):
                        return None
                    hostname = typer.prompt("SSH Hostname (e.g., ssh.example.com)")
                    service = "ssh://localhost:22"
                else:
                    if typer.confirm("Skip DNS routing for this service?", default=False):
                        hostname = "*"
                    else:
                        hostname = typer.prompt("Hostname (e.g., app.example.com)")
                        
                        if hostname != "*":
                            try:
                                run_command(["cloudflared", "tunnel", "route", "dns", "--overwrite-dns", tunnel_id, hostname], check=True)
                                console.print(f"[green]DNS routed for {hostname}[/green]")
                            except Exception as e:
                                console.print(f"[red]Failed to route DNS: {e}[/red]")
                                if not typer.confirm("Continue anyway?", default=True):
                                    return None

                    service = typer.prompt("Local Service URL", default="http://localhost:8000")
                
                return {"hostname": hostname, "service": service}

        # Primary HTTP Service
        console.print("\n[bold cyan]--- Primary Web Service ---[/bold cyan]")
        primary = add_service_prompt("http")
        if primary: ingress_rules.append(primary)
        
        # SSH Service
        console.print("\n[bold cyan]--- SSH Access ---[/bold cyan]")
        ssh_service = add_service_prompt("ssh")
        if ssh_service: ingress_rules.append(ssh_service)
        
        # Additional Services
        while typer.confirm("\nDo you want to add another service?", default=False):
            extra = add_service_prompt("http")
            if extra: ingress_rules.append(extra)
            
        # Add 404 fallback
        ingress_rules.append({"service": "http_status:404"})

    else:
        # Client-to-Client / Site-to-Site Mode
        warp_routing_enabled = True
        console.print("\n[bold cyan]--- Private Network Subnet Routing (Site-to-Site VPN) ---[/bold cyan]")
        local_cidr = Prompt.ask("Enter Local Subnet CIDR to advertise (e.g. 192.168.10.0/24)", default="192.168.10.0/24")
        remote_cidr = Prompt.ask("Enter Remote Target Subnet CIDR (Peer Network)", default="192.168.20.0/24")

        console.print(f"[cyan]Routing local CIDR {local_cidr} to Tunnel {tunnel_id}...[/cyan]")
        try:
            run_command(["cloudflared", "tunnel", "route", "ip", "add", local_cidr, tunnel_id], check=False)
            console.print(f"[green]✓ Route for {local_cidr} registered on Cloudflare Private Network[/green]")
        except Exception as e:
            console.print(f"[yellow]Note on IP route registration: {e}[/yellow]")

        ingress_rules.append({
            "hostname": f"{local_cidr} [Site-to-Site]",
            "service": f"WARP Routing (Peer: {remote_cidr})"
        })
        ingress_rules.append({"service": "http_status:404"})

    # 5. Generate Config
    config_data = {
        "tunnel": tunnel_id,
        "credentials-file": str(cred_path),
    }
    if warp_routing_enabled:
        config_data["warp-routing"] = {"enabled": True}
    config_data["ingress"] = ingress_rules
    
    TUNNEL_DIR.mkdir(exist_ok=True)
    
    # Save atomically with 0600 permissions
    tmp_config = CONFIG_FILE.with_suffix(".tmp")
    with open(tmp_config, "w") as f:
        yaml.dump(config_data, f, sort_keys=False)
    os.chmod(tmp_config, 0o600)
    os.replace(tmp_config, CONFIG_FILE)
        
    console.print(f"[green]Configuration saved securely to {CONFIG_FILE.absolute()}[/green]")
    
    time.sleep(1)
    step_index += 1
    
    # 6. Run
    refresh_interface(step_index)
    console.print("You can now run the tunnel.")
    
    if Confirm.ask("Do you want to run the tunnel now?"):
        cred_path = Path.home() / ".cloudflared" / f"{tunnel_id}.json"
        start_tunnel_background(tunnel_id, CONFIG_FILE, cred_path)

def _start():
    if is_tunnel_running():
        console.print("[yellow]Tunnel is already running. Use 'tunnelflare stop' to stop it first.[/yellow]")
        return

    if not CONFIG_FILE.exists():
        console.print(f"[red]No configuration file found at {CONFIG_FILE}.[/red]")
        console.print("[yellow]Please run 'tunnelflare setup' to create a new tunnel configuration.[/yellow]")
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f)
        
        tunnel_id = config.get("tunnel")
        if not tunnel_id:
            console.print("[red]Invalid configuration: Tunnel ID missing.[/red]")
            console.print("[yellow]Your configuration file seems corrupted. Please run 'tunnelflare setup' to reconfigure.[/yellow]")
            return
            
        console.print(f"[green]Found configuration for Tunnel ID: {tunnel_id}[/green]")
        
        # Validate Credentials File
        cred_file = config.get("credentials-file")
        if cred_file:
            cred_path = Path(cred_file)
            if not cred_path.exists():
                console.print(f"[red]Error: Credentials file not found at {cred_path}[/red]")
                
                if str(cred_path).startswith("/root") and os.geteuid() != 0:
                     console.print("[yellow]Warning: The configuration points to a file in /root, but you are not running as root.[/yellow]")
                     console.print("[yellow]This usually happens if you ran 'setup' with sudo previously.[/yellow]")
                     console.print("[bold]Solution:[/bold] Run [cyan]tunnelflare reset[/cyan] and then [cyan]tunnelflare setup[/cyan] (without sudo).")
                     return
                else:
                     console.print("[yellow]Your tunnel credentials seem to be missing.[/yellow]")
                     console.print("[bold]Solution:[/bold] Run [cyan]tunnelflare reset[/cyan] and then [cyan]tunnelflare setup[/cyan] to regenerate them.")
                     return
        else:
             console.print("[red]Error: Credentials file not defined in configuration.[/red]")
             return
        
        start_tunnel_background(tunnel_id, CONFIG_FILE, cred_path)
        
    except Exception as e:
        console.print(f"[red]Failed to start tunnel: {e}[/red]")
        console.print("[yellow]Check the logs for more details.[/yellow]")

@app.command()
def start():
    """
    Start the tunnel using the existing configuration.
    """
    refresh_interface(-1)
    _start()

@app.command()
def status():
    """
    Show live interactive status dashboard (Textual TUI).
    """
    try:
        from tui import TunnelFlareApp
        app = TunnelFlareApp()
        app.run()
    except ImportError:
        console.print("[red]Textual is not installed. Please run './install.sh' again.[/red]")
    except Exception as e:
        console.print(f"[red]Error launching dashboard: {e}[/red]")

def _stop():
    pid = is_tunnel_running()
    if not pid:
        console.print("[red]Tunnel is not running. No process to stop.[/red]")
        return
    
    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Stopped tunnel process (PID: {pid}).[/green]")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        console.print(f"[red]Failed to stop tunnel: {e}[/red]")

@app.command()
def stop():
    """
    Stop the background tunnel process.
    """
    refresh_interface(-1)
    _stop()

@app.command()
def restart():
    """
    Restart the tunnel process.
    """
    refresh_interface(-1)
    console.print("[bold cyan]Restarting TunnelFlare...[/bold cyan]")
    _stop()
    time.sleep(2)
    _start()

@app.command()
def install():
    """
    Install cloudflared on the system.
    """
    refresh_interface(-1)
    if check_cloudflared_installed():
        console.print("[green]cloudflared is already installed.[/green]")
    else:
        if install_cloudflared():
            console.print("[green]cloudflared installed successfully![/green]")
        else:
            console.print("[red]Failed to install cloudflared.[/red]")

@app.command()
def reset():
    """
    Reset TunnelFlare settings and configurations.
    """
    refresh_interface(-1)
    console.print(f"[{CLOUDFLARE_ORANGE}]Resetting TunnelFlare...[/{CLOUDFLARE_ORANGE}]")
    
    # 1. Remove config.yml
    if CONFIG_FILE.exists():
        if Confirm.ask(f"Remove local configuration file ({CONFIG_FILE.absolute()})?"):
            try:
                CONFIG_FILE.unlink()
                console.print("[green]Configuration file removed.[/green]")
            except Exception as e:
                console.print(f"[red]Failed to remove config file: {e}[/red]")
    else:
        console.print("[yellow]No secure configuration file found.[/yellow]")

    # 2. Remove .cloudflared directory (Optional)
    cloudflared_dir = Path.home() / ".cloudflared"
    if cloudflared_dir.exists():
        console.print(f"\n[bold red]Warning:[/] This will remove all Cloudflare Tunnel credentials and certificates in {cloudflared_dir}.")
        if Confirm.ask("Do you want to remove the .cloudflared directory (Factory Reset)?"):
            try:
                import shutil
                shutil.rmtree(cloudflared_dir)
                console.print("[green].cloudflared directory removed.[/green]")
            except Exception as e:
                console.print(f"[red]Failed to remove .cloudflared directory: {e}[/red]")
    
    console.print("\n[green]Reset complete.[/green]")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host interface to bind the web server"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run web server as a background daemon"),
):
    """
    Launch the TunnelFlare Hybrid Web Mesh Dashboard (React Flow canvas & map UI).
    """
    refresh_interface(-1)
    console.print(f"[{CLOUDFLARE_ORANGE}]Starting TunnelFlare Web Mesh Control Plane...[/{CLOUDFLARE_ORANGE}]")
    console.print(f"[bold cyan]Local Dashboard:[/]  http://localhost:{port}")
    if host == "0.0.0.0":
        primary_ip = None
        for iface in utils.get_active_interfaces():
            if iface.get("is_up") and iface.get("primary_ip"):
                primary_ip = iface["primary_ip"].split("/")[0]
                break
        if primary_ip:
            console.print(f"[bold cyan]Network Access:[/]   http://{primary_ip}:{port}")
    console.print(f"[dim]Interactive REST API & OpenAPI Docs:[/] http://localhost:{port}/docs\n")

    from web_server import run_web_server
    if daemon:
        import subprocess
        log_file = TUNNEL_DIR / "web.log"
        with open(log_file, "a") as out:
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "web_server:app", "--host", host, "--port", str(port)],
                stdout=out,
                stderr=out,
                start_new_session=True,
            )
        console.print(f"[green]Web server running in background (PID: {proc.pid}). Logs: {log_file}[/green]")
    else:
        run_web_server(host=host, port=port)


# -------------------------------------------------------------
# Account Sub-App: Cloudflare Zero Trust Authentication
# -------------------------------------------------------------
account_app = typer.Typer(help="Manage Cloudflare Zero Trust account credentials and authentication.")
app.add_typer(account_app, name="account")


@account_app.command("login")
def account_login(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Cloudflare Zero Trust API Token"),
    account_id: Optional[str] = typer.Option(None, "--account-id", "-a", help="Cloudflare Account ID (optional, auto-detected)"),
    site_name: Optional[str] = typer.Option(None, "--site", "-s", help="Local Site Name / Identifier"),
):
    """
    Authenticate and link your Cloudflare Zero Trust account.
    """
    refresh_interface(-1)
    import cloudflare_api

    if not token:
        token = Prompt.ask("[bold cyan]Enter Cloudflare Zero Trust API Token[/bold cyan]", password=True)
    if not token or not token.strip():
        console.print("[red]Error: API token cannot be empty.[/red]")
        raise typer.Exit(1)

    console.print("[yellow]Verifying token permissions with Cloudflare...[/yellow]")
    client = cloudflare_api.CloudflareClient(token=token.strip())
    try:
        verify_res = client.verify_token()
        accounts = client.get_accounts()
    except cloudflare_api.CloudflareAPIError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)

    if not accounts:
        console.print("[red]Error: No Cloudflare accounts found with this token.[/red]")
        raise typer.Exit(1)

    selected_account = accounts[0]
    if account_id:
        match = next((a for a in accounts if a.get("id") == account_id), None)
        if match:
            selected_account = match
        else:
            console.print(f"[yellow]Warning: Account ID '{account_id}' not found in list, using {selected_account.get('id')}[/yellow]")

    acc_id = selected_account.get("id")
    acc_name = selected_account.get("name", "Primary Account")
    site = site_name or f"Site-{socket.gethostname()}"

    cloudflare_api.save_account_config(
        token=token.strip(),
        account_id=acc_id,
        account_name=acc_name,
        site_name=site,
    )

    console.print(f"[green]Successfully authenticated and linked Cloudflare account![/green]")
    table = Table(box=box.ROUNDED, border_style=CYBER_CYAN)
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_row("Account Name", acc_name)
    table.add_row("Account ID", acc_id)
    table.add_row("Site Identifier", site)
    table.add_row("Token Status", verify_res.get("status", "active").upper())
    console.print(table)


@account_app.command("status")
def account_status():
    """
    View currently linked Cloudflare Zero Trust account.
    """
    refresh_interface(-1)
    import cloudflare_api

    cfg = cloudflare_api.load_account_config()
    if not cfg:
        console.print("[yellow]No Cloudflare Zero Trust account linked.[/yellow]")
        console.print("[dim]Run 'tunnelflare account login' or open 'tunnelflare web' to authenticate.[/dim]")
        return

    table = Table(title="Cloudflare Zero Trust Account", box=box.ROUNDED, border_style=CLOUDFLARE_ORANGE)
    table.add_column("Key", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_row("Account Name", cfg.get("account_name", "Unknown"))
    table.add_row("Account ID", cfg.get("account_id", "Unknown"))
    table.add_row("Site Name", cfg.get("site_name", "Unknown"))
    table.add_row("Credentials Path", str(cloudflare_api.ACCOUNT_FILE))

    client = cloudflare_api.CloudflareClient(token=cfg.get("token"))
    try:
        ver = client.verify_token()
        table.add_row("Token Health", f"[green]VERIFIED ({ver.get('status', 'active').upper()})[/green]")
    except Exception as e:
        table.add_row("Token Health", f"[red]INVALID: {e}[/red]")

    console.print(table)


@account_app.command("logout")
def account_logout():
    """
    Remove saved Cloudflare Zero Trust credentials.
    """
    refresh_interface(-1)
    import cloudflare_api

    cloudflare_api.clear_account_config()
    console.print("[green]Cloudflare Zero Trust account configuration removed.[/green]")


# -------------------------------------------------------------
# Mesh Sub-App: Site-to-Site Zero Trust Mesh Routes
# -------------------------------------------------------------
mesh_app = typer.Typer(help="Manage Zero Trust site-to-site mesh routes and peers.")
app.add_typer(mesh_app, name="mesh")


@mesh_app.command("list")
def mesh_list():
    """
    List all discovered tunnels and registered CIDR private network routes.
    """
    refresh_interface(-1)
    import cloudflare_api

    cfg = cloudflare_api.load_account_config()
    if not cfg:
        console.print("[yellow]Cloudflare account not linked. Run 'tunnelflare account login' first.[/yellow]")
        return

    client = cloudflare_api.CloudflareClient(token=cfg.get("token"), account_id=cfg.get("account_id"))
    try:
        tunnels = client.list_tunnels(is_deleted=False)
        routes = client.list_routes(is_deleted=False)
    except cloudflare_api.CloudflareAPIError as e:
        console.print(f"[red]Failed to query Cloudflare Zero Trust API: {e}[/red]")
        return

    console.print(f"\n[{CLOUDFLARE_ORANGE}]Discovered Mesh Tunnels ({len(tunnels)}):[/{CLOUDFLARE_ORANGE}]")
    t_table = Table(box=box.ROUNDED, border_style=CYBER_CYAN)
    t_table.add_column("Tunnel Name", style="bold white")
    t_table.add_column("Tunnel ID", style="dim")
    t_table.add_column("Status", style="green")
    t_table.add_column("Connections", style="cyan")

    for t in tunnels:
        conns = t.get("connections", [])
        colo = conns[0].get("colo_name", "EDGE") if conns else "OFFLINE"
        status = t.get("status", "inactive")
        status_color = "green" if status == "healthy" else ("yellow" if status == "degraded" else "red")
        t_table.add_row(t.get("name", ""), t.get("id", "")[:12] + "...", f"[{status_color}]{status.upper()}[/{status_color}]", f"{len(conns)} active ({colo})")
    console.print(t_table)

    console.print(f"\n[{NEON_EMERALD}]Registered Private Network CIDR Routes ({len(routes)}):[/{NEON_EMERALD}]")
    r_table = Table(box=box.ROUNDED, border_style=NEON_EMERALD)
    r_table.add_column("Subnet CIDR", style="bold green")
    r_table.add_column("Route ID", style="dim")
    r_table.add_column("Gateway Tunnel ID", style="cyan")
    r_table.add_column("Comment / Note", style="white")

    for r in routes:
        r_table.add_row(r.get("network", ""), r.get("id", "")[:12] + "...", r.get("tunnel_id", "")[:12] + "...", r.get("comment", ""))
    console.print(r_table)


@mesh_app.command("route-add")
def mesh_route_add(
    network: str = typer.Argument(..., help="Subnet CIDR to route (e.g. 192.168.20.0/24)"),
    tunnel_id: Optional[str] = typer.Option(None, "--tunnel", "-t", help="Target tunnel ID (defaults to active local tunnel)"),
    comment: str = typer.Option("TunnelFlare Mesh Route", "--comment", "-c", help="Route description"),
):
    """
    Register a private subnet CIDR to route through a Cloudflare Tunnel gateway.
    """
    refresh_interface(-1)
    import cloudflare_api

    cfg = cloudflare_api.load_account_config()
    if not cfg:
        console.print("[yellow]Cloudflare account not linked. Run 'tunnelflare account login' first.[/yellow]")
        return

    client = cloudflare_api.CloudflareClient(token=cfg.get("token"), account_id=cfg.get("account_id"))
    t_id = tunnel_id
    if not t_id:
        tunnels = client.list_tunnels(is_deleted=False)
        if not tunnels:
            console.print("[red]No active tunnels found in this account.[/red]")
            return
        t_id = tunnels[0]["id"]
        console.print(f"[dim]Auto-selected tunnel: {tunnels[0].get('name')} ({t_id})[/dim]")

    try:
        res = client.add_cidr_route(network=network, tunnel_id=t_id, comment=comment)
        console.print(f"[green]Successfully registered CIDR route {network} to tunnel {t_id}![/green]")
    except cloudflare_api.CloudflareAPIError as e:
        console.print(f"[red]Failed to add route: {e}[/red]")


@mesh_app.command("route-del")
def mesh_route_del(
    route_id: str = typer.Argument(..., help="Cloudflare route UUID to revoke"),
):
    """
    Revoke a registered private network CIDR route.
    """
    refresh_interface(-1)
    import cloudflare_api

    cfg = cloudflare_api.load_account_config()
    if not cfg:
        console.print("[yellow]Cloudflare account not linked. Run 'tunnelflare account login' first.[/yellow]")
        return

    client = cloudflare_api.CloudflareClient(token=cfg.get("token"), account_id=cfg.get("account_id"))
    try:
        client.delete_cidr_route(route_id=route_id)
        console.print(f"[green]Successfully deleted route {route_id}![/green]")
    except cloudflare_api.CloudflareAPIError as e:
        console.print(f"[red]Failed to delete route: {e}[/red]")


if __name__ == "__main__":

    app()

