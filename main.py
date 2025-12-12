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

from utils import check_cloudflared_installed, install_cloudflared, run_command

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
        with console.status(f"[bold green]Creating tunnel '{tunnel_name}'...[/bold green]"):
            output = run_command(["cloudflared", "tunnel", "create", tunnel_name], check=False)
        
        if output and "Tunnel credentials written" in output:
             console.print(f"[green]Tunnel '{tunnel_name}' created successfully![/green]")
        elif output and "already exists" in output:
             console.print(f"[yellow]Tunnel '{tunnel_name}' already exists. Using existing tunnel.[/yellow]")
        
        # Get Tunnel ID
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
    if Confirm.ask("Do you want to route a DNS hostname now?", default=True):
        domain = Prompt.ask("Enter the hostname you want to assign (e.g., app.example.com)")
        try:
            with console.status(f"[bold green]Routing {domain} to tunnel...[/bold green]"):
                run_command(["cloudflared", "tunnel", "route", "dns", tunnel_id, domain], check=True)
            console.print(f"[green]Successfully routed {domain} to tunnel![/green]")
        except Exception as e:
            console.print(f"[red]Failed to route DNS: {e}[/red]")
            console.print("[yellow]You can try routing it manually later using 'cloudflared tunnel route dns <UUID> <HOSTNAME>'.[/yellow]")
    else:
        domain = Prompt.ask("Enter the hostname you PLAN to use (for config generation)", default="app.example.com")
        console.print("[yellow]Skipping DNS routing. You will need to add a CNAME record manually.[/yellow]")

    time.sleep(1)
    step_index += 1

    # 5. Configuration
    refresh_interface(step_index)
    local_service = Prompt.ask("Enter your local service URL", default="http://localhost:8000")
    
    config_content = {
        "tunnel": tunnel_id,
        "credentials-file": str(Path.home() / ".cloudflared" / f"{tunnel_id}.json"),
        "ingress": [
            {
                "hostname": domain,
                "service": local_service
            },
            {
                "service": "http_status:404"
            }
        ]
    }
    
    # Ensure directory exists
    TUNNEL_DIR.mkdir(exist_ok=True)
    
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_content, f, sort_keys=False)
        
    # Set permissions to 600 (Read/Write for owner only)
    os.chmod(CONFIG_FILE, 0o600)
    
    console.print(f"[green]Configuration saved securely to {CONFIG_FILE.absolute()}[/green]")
    
    time.sleep(1)
    step_index += 1
    
    # 6. Run
    refresh_interface(step_index)
    console.print("You can now run the tunnel.")
    
    if Confirm.ask("Do you want to run the tunnel now?"):
        start_tunnel_background(tunnel_name)

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

if __name__ == "__main__":
    app()
