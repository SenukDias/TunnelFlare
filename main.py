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
import yaml

from utils import (
    check_cloudflared_installed, 
    install_cloudflared, 
    run_command,
    get_local_cidr,
    add_ip_route,
    list_ip_routes,
    get_split_tunnel_json
)
try:
    from connector_template import WARP_CONNECTOR_COMPOSE, DASHBOARD_HTML, DASHBOARD_SERVER
except ImportError:
    WARP_CONNECTOR_COMPOSE = ""
    DASHBOARD_HTML = "<h1>Error: Missing Template</h1>"
    DASHBOARD_SERVER = "print('Error: Missing Template')"

app = typer.Typer()
console = Console()

CLOUDFLARE_ORANGE = "#F38020"
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
    "Check Dependencies",
    "Authentication",
    "Create Tunnel",
    "Route DNS",
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
            
    steps_panel = Panel(Align.center(steps_text), title="Setup Progress", border_style=CLOUDFLARE_ORANGE)
    
    return Group(logo_panel, steps_panel)

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

@app.command()
def setup():
    """
    Interactive setup wizard for Cloudflare Tunnel.
    """
    step_index = 0
    
    # 1. Check Dependencies
    refresh_interface(step_index)
    console.print(f"[{CLOUDFLARE_ORANGE}]Checking Dependencies...[/{CLOUDFLARE_ORANGE}]")
    if not check_cloudflared_installed():
        console.print("[red]cloudflared is not installed.[/red]")
        if Confirm.ask("Do you want to install it now?"):
            if install_cloudflared():
                console.print("[green]cloudflared installed successfully![/green]")
            else:
                console.print("[red]Failed to install cloudflared. Please try installing it manually (e.g., 'sudo apt install cloudflared').[/red]")
                raise typer.Exit(code=1)
        else:
            console.print("[yellow]Cloudflared is required to continue. Please install it and run setup again.[/yellow]")
            raise typer.Exit(code=1)
    else:
        console.print("[green]cloudflared is already installed.[/green]")
    
    time.sleep(1)
    step_index += 1

    # 2. Login
    refresh_interface(step_index)
    cert_path = Path.home() / ".cloudflared" / "cert.pem"
    if not cert_path.exists():
        console.print("You need to login to Cloudflare.")
        console.print("A browser window will open. Please select your domain.")
        if Confirm.ask("Ready to login?"):
            try:
                console.print("[cyan]Launching Cloudflare login...[/cyan]")
                console.print("[yellow]Please click the URL below if it doesn't open automatically:[/yellow]")
                run_command(["cloudflared", "tunnel", "login"], check=True, capture_output=False)
                console.print("[green]Login successful![/green]")
            except Exception:
                console.print("[red]Login failed or was cancelled. Please check your internet connection and try again.[/red]")
                raise typer.Exit(code=1)
    else:
        console.print(f"[green]Already logged in.[/green] (Found {cert_path})")
    
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
                     console.print(f"[red]But local credentials are missing for ID {tunnel_id}.[/red]")
                     console.print("[cyan]Deleting old remote tunnel to recreate it...[/cyan]")
                     run_command(["cloudflared", "tunnel", "delete", "-f", tunnel_name], check=False)
                     
                     # Try creating again
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

    # 4. Route DNS
    refresh_interface(step_index)
    
    domain = ""
    # 4. Route DNS & Configure Services
    refresh_interface(step_index)
    
    cred_path = Path.home() / ".cloudflared" / f"{tunnel_id}.json"
    ingress_rules = []
    
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
                    
                    # Route DNS if not wildcard
                    if hostname != "*":
                        try:
                            run_command(["cloudflared", "tunnel", "route", "dns", tunnel_id, hostname], check=True)
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
    
    # 5. Generate Config
    config_data = {
        "tunnel": tunnel_id,
        "credentials-file": str(cred_path),
        "ingress": ingress_rules
    }

    # VPN Mode / WARP Routing
    warp_enabled = False
    console.print("\n[bold cyan]--- VPN / Private Network Mode ---[/bold cyan]")
    console.print("This allows you to access this network remotely via WARP (Site-to-Site).")
    if Confirm.ask("Enable VPN Mode (WARP Routing)?", default=False):
        config_data["warp-routing"] = {"enabled": True}
        warp_enabled = True
        console.print("[green]WARP Routing Enabled.[/green]")
        
        # Check if we should add the local CIDR immediately
        local_cidr = get_local_cidr()
        if local_cidr:
            if Confirm.ask(f"Route local network {local_cidr}?", default=True):
                 if add_ip_route(tunnel_id, local_cidr):
                     console.print(f"[green]Added route for {local_cidr}[/green]")
                     console.print("[yellow]Note: You still need to split-tunnel this IP in Zero Trust dashboard.[/yellow]")
                 else:
                     console.print(f"[red]Failed to add route for {local_cidr}. You can try later with 'tunnelflare vpn-add'.[/red]")

        # Offer Docker Compose for WARP Connector
        # Offer Docker Compose for WARP Connector
        if Confirm.ask("Generate docker-compose.yml for WARP Connector?", default=False):
             # Create directory structure
             connector_dir = TUNNEL_DIR / "connector"
             dashboard_dir = connector_dir / "dashboard"
             connector_dir.mkdir(exist_ok=True)
             dashboard_dir.mkdir(exist_ok=True)
             
             # Write Docker Compose
             with open(connector_dir / "docker-compose.yml", "w") as f:
                 f.write(WARP_CONNECTOR_COMPOSE)
                 
             # Write Dashboard Files
             with open(dashboard_dir / "index.html", "w") as f:
                 f.write(DASHBOARD_HTML)
                 
             with open(dashboard_dir / "server.py", "w") as f:
                 f.write(DASHBOARD_SERVER)
             
             console.print(f"[green]Generated Connector Project in {connector_dir}[/green]")
             console.print("[cyan]To run: cd ~/.tunnelflare/connector && docker-compose up -d[/cyan]")
             console.print("[cyan]Dashboard will be available at http://localhost:8080[/cyan]")
    
    
    # Ensure directory exists
    TUNNEL_DIR.mkdir(exist_ok=True)
    
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f, sort_keys=False)
        
    # Set permissions to 600 (Read/Write for owner only)
    os.chmod(CONFIG_FILE, 0o600)
    
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
def vpn_add(cidr: str = typer.Argument(None, help="The CIDR to route (e.g. 192.168.1.0/24). Auto-detects if omitted.")):
    """
    Add a private IP route (CIDR) to the tunnel.
    """
    refresh_interface(-1)
    
    # Check config for tunnel ID
    if not CONFIG_FILE.exists():
        console.print("[red]No configuration found. Run 'setup' first.[/red]")
        return

    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
    
    tunnel_id = config.get("tunnel")
    if not tunnel_id:
        console.print("[red]Tunnel ID not found in config.[/red]")
        return
        
    # Auto-detect if not provided
    if not cidr:
        console.print("[cyan]Auto-detecting local network...[/cyan]")
        cidr = get_local_cidr()
        if not cidr:
            console.print("[red]Could not detect local network. Please specify CIDR manually.[/red]")
            return
        if not Confirm.ask(f"Route network {cidr}?", default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return
            
    console.print(f"Adding route for [bold]{cidr}[/bold] to tunnel {tunnel_id[:8]}...")
    
    if add_ip_route(tunnel_id, cidr):
        console.print(f"[green]Successfully added route: {cidr}[/green]")
        console.print("\n[bold white]Next Steps (Split Tunneling):[/bold white]")
        console.print("Add this to your Split Tunnel 'Include' list in Cloudflare Zero Trust:")
        
        json_out = get_split_tunnel_json(cidr)
        console.print(Panel(json_out, title="JSON Configuration", border_style="cyan"))
        
        # Check if warp-routing is enabled in config, if not, warn
        if "warp-routing" not in config or not config["warp-routing"].get("enabled"):
             console.print("[bold yellow]Warning:[/] 'warp-routing' is NOT enabled in your config.yml.")
             if Confirm.ask("Enable 'warp-routing' in config now?"):
                 config["warp-routing"] = {"enabled": True}
                 with open(CONFIG_FILE, "w") as f:
                     yaml.dump(config, f, sort_keys=False)
                 console.print("[green]Updated config.yml. Please restart the tunnel.[/green]")
    else:
        console.print("[red]Failed to add route. Check connectivity or permissions.[/red]")

@app.command()
def vpn_status():
    """
    Show active VPN routes for this tunnel.
    """
    refresh_interface(-1)
    
    if not CONFIG_FILE.exists():
        console.print("[red]No configuration found.[/red]")
        return

    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)
        
    tunnel_id = config.get("tunnel")
    if not tunnel_id:
         console.print("[red]Tunnel ID missing.[/red]")
         return
         
    routes = list_ip_routes(tunnel_id)
    
    if not routes:
        console.print("[yellow]No active IP routes found for this tunnel.[/yellow]")
        console.print("Use [cyan]tunnelflare vpn-add[/cyan] to add one.")
        return
        
    table = Table(title=f"Active IP Routes ({tunnel_id[:8]}...)", border_style=CLOUDFLARE_ORANGE)
    table.add_column("Network (CIDR)", style="cyan")
    table.add_column("Virtual Net ID", style="dim")
    table.add_column("Comments", style="white")
    
    for r in routes:
        table.add_row(
            r.get("network", "N/A"),
            r.get("vnet_id", "N/A"),
            r.get("comment", "") or r.get("created_at", "") # Fallback to created time or empty
        )
        
    console.print(table)

    app()
