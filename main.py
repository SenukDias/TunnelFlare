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

def get_header(current_step_index: int = -1):
    """
    Returns a renderable group containing the Logo and the Step Progress.
    """
    # Logo
    logo_panel = Align.center(Text.from_markup(TUNNEL_FLARE_LOGO))
    
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

def generate_pixel_animation(width=60, height=10):
    """Generates a random pixelated animation frame."""
    chars = ["█", "▓", "▒", "░", " "]
    colors = [CLOUDFLARE_ORANGE, "orange1", "orange3", "grey30"]
    
    grid = Table.grid(expand=True)
    for _ in range(height):
        row_text = Text()
        for _ in range(width):
            char = random.choice(chars)
            color = random.choice(colors)
            row_text.append(char, style=color)
        grid.add_row(Align.center(row_text))
    return grid

def generate_tree_topology_animation(frame_count, tunnel_id, ingress_rules):
    """
    Generates a vertical ASCII network topology animation with a Tree for services.
    """
    # Animation frame logic
    pos = frame_count % 4
    
    def get_arrow():
        if pos == 0: return "↓"
        if pos == 1: return "."
        if pos == 2: return "."
        return "."

    def get_arrow_2():
        if pos == 1: return "↓"
        if pos == 2: return "."
        if pos == 3: return "."
        return "."
        
    def get_arrow_3():
        if pos == 2: return "↓"
        if pos == 3: return "."
        if pos == 0: return "."
        return "."
        
    # Nodes - Compacted
    user_node = Panel(Align.center(Text("👤 Client\nIP: Detected (Dynamic)", style="bold cyan")), border_style="cyan", width=35, padding=(0, 1))
    internet_node = Panel(Align.center(Text("🌐 Internet\nRoute: Public Web", style="bold white")), border_style="white", width=35, padding=(0, 1))
    cloudflare_node = Panel(Align.center(Text("☁️  Cloudflare\nIP: Anycast Network", style=f"bold {CLOUDFLARE_ORANGE}")), border_style=CLOUDFLARE_ORANGE, width=35, padding=(0, 1))
    
    # Tunnel Node
    tunnel_text = Text(f"🚇 Tunnel\nUUID: {tunnel_id[:8]}...\nStatus: Connected", style="bold green")
    tunnel_node = Panel(Align.center(tunnel_text), border_style="green", width=35, padding=(0, 1))
    
    # Tree for Services
    service_tree = Tree(f"[bold yellow]🏠 Local Network[/bold yellow]")
    
    if ingress_rules:
        for rule in ingress_rules:
            hostname = rule.get("hostname", "*")
            service = rule.get("service", "N/A")
            
            if service == "http_status:404":
                continue
                
            # Node Label
            label = Text()
            label.append("🔗 ", style="bold blue")
            label.append(f"{hostname}", style="bold white")
            label.append(f"\n   ↳ {service}", style="dim yellow")
            
            service_tree.add(label)
    else:
        service_tree.add("[dim]No active services[/dim]")

    # Arrows
    arrow_style = f"bold {CLOUDFLARE_ORANGE}"
    
    # Layout using a Table to stack vertically
    grid = Table.grid(expand=True, padding=0)
    grid.add_column(justify="center")
    
    grid.add_row(user_node)
    grid.add_row(Text(get_arrow(), style=arrow_style))
    
    grid.add_row(internet_node)
    grid.add_row(Text(get_arrow_2(), style=arrow_style))
    
    grid.add_row(cloudflare_node)
    grid.add_row(Text(get_arrow_3(), style=arrow_style))
    
    grid.add_row(tunnel_node)
    
    # Add the tree below the tunnel
    grid.add_row(Text("│", style=arrow_style))
    grid.add_row(Align.center(service_tree))
    
    return Align.center(grid)

def get_resource_table():
    """
    Reads config.yml and returns a table of resources.
    """
    config_file = Path("config.yml")
    if not config_file.exists():
        return Text("No config.yml found.", style="red")
    
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        table = Table(expand=True, border_style=CLOUDFLARE_ORANGE)
        table.add_column("Ingress Rule (DNS)", style="cyan")
        table.add_column("Local Service", style="yellow")
        
        if "ingress" in config:
            for rule in config["ingress"]:
                hostname = rule.get("hostname", "*")
                service = rule.get("service", "N/A")
                table.add_row(hostname, service)
        
        return table
    except Exception as e:
        return Text(f"Error reading config: {e}", style="red")

def get_config_details():
    """Reads config.yml and returns tunnel_id and all ingress rules."""
    config_file = Path("config.yml")
    tunnel_id = "Unknown"
    ingress_rules = []
    
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
                tunnel_id = config.get("tunnel", "Unknown")
                ingress_rules = config.get("ingress", [])
        except:
            pass
    return tunnel_id, ingress_rules

def start_tunnel_background(tunnel_name: str):
    """
    Starts the tunnel in the background and saves the PID.
    """
    TUNNEL_DIR.mkdir(exist_ok=True)
    
    with open(LOG_FILE, "w") as log:
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "run", tunnel_name],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True # Detach from terminal
        )
    
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))
        
    console.print(f"[green]Tunnel '{tunnel_name}' started in background (PID: {process.pid}).[/green]")
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
                console.print("[red]Failed to install cloudflared. Please install it manually.[/red]")
                raise typer.Exit(code=1)
        else:
            console.print("[yellow]Please install cloudflared to continue.[/yellow]")
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
                with console.status("[bold green]Waiting for login...[/bold green]"):
                    run_command(["cloudflared", "tunnel", "login"], check=True)
                console.print("[green]Login successful![/green]")
            except Exception:
                console.print("[red]Login failed or was cancelled.[/red]")
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
        raise typer.Exit(code=1)

    time.sleep(1)
    step_index += 1

    # 4. Route DNS
    refresh_interface(step_index)
    domain = Prompt.ask("Enter the hostname you want to assign (e.g., app.example.com)")
    
    try:
        with console.status(f"[bold green]Routing {domain} to tunnel...[/bold green]"):
            run_command(["cloudflared", "tunnel", "route", "dns", tunnel_id, domain], check=True)
        console.print(f"[green]Successfully routed {domain} to tunnel![/green]")
    except Exception as e:
        console.print(f"[red]Failed to route DNS: {e}[/red]")

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
    
    config_file = Path("config.yml")
    with open(config_file, "w") as f:
        yaml.dump(config_content, f, sort_keys=False)
    
    console.print(f"[green]Configuration saved to {config_file.absolute()}[/green]")
    
    time.sleep(1)
    step_index += 1
    
    # 6. Run
    refresh_interface(step_index)
    console.print("You can now run the tunnel.")
    
    if Confirm.ask("Do you want to run the tunnel now?"):
        start_tunnel_background(tunnel_name)

@app.command()
def start():
    """
    Start the tunnel using the existing configuration.
    """
    refresh_interface(-1)
    
    if is_tunnel_running():
        console.print("[yellow]Tunnel is already running.[/yellow]")
        return

    config_file = Path("config.yml")
    if not config_file.exists():
        console.print("[red]No configuration file found. Please run 'setup' first.[/red]")
        return

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        tunnel_id = config.get("tunnel")
        if not tunnel_id:
            console.print("[red]Invalid configuration: Tunnel ID missing.[/red]")
            return
            
        # We can run by ID or Name. Since we stored ID in config, let's try running by ID.
        # cloudflared tunnel run <UUID> works.
        
        console.print(f"[green]Found configuration for Tunnel ID: {tunnel_id}[/green]")
        start_tunnel_background(tunnel_id)
        
    except Exception as e:
        console.print(f"[red]Failed to start tunnel: {e}[/red]")

@app.command()
def status():
    """
    Show live status, network topology, and resources of the running tunnel.
    """
    pid = is_tunnel_running()
    if not pid:
        console.print("[red]Tunnel is not running.[/red]")
        return

    console.clear()
    
    # Get details for topology
    tunnel_id, ingress_rules = get_config_details()
    
    layout = Layout()
    
    # New Layout Strategy:
    # Top: Header (Logo) - Fixed size
    # Bottom: Body
    #   Body Left: Topology (Wider)
    #   Body Right: Resources (Top, Larger) + Logs (Bottom, Smaller)
    
    layout.split(
        Layout(name="header", size=8),
        Layout(name="body")
    )
    
    layout["header"].update(Align.center(Text.from_markup(TUNNEL_FLARE_LOGO)))
    
    layout["body"].split_row(
        Layout(name="left", ratio=3), # Wider Topology
        Layout(name="right", ratio=2)
    )
    
    layout["right"].split(
        Layout(name="resources", ratio=2), # Larger Resources
        Layout(name="logs", ratio=1) # Smaller Logs
    )
    
    frame_count = 0
    
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            # Check if still running
            if not is_tunnel_running():
                console.print("[red]Tunnel stopped unexpectedly.[/red]")
                break

            # Update Topology Animation
            layout["left"].update(Panel(generate_tree_topology_animation(frame_count, tunnel_id, ingress_rules), title="[bold white]NETWORK TOPOLOGY[/]", border_style=CLOUDFLARE_ORANGE))
            
            # Update Resources
            layout["resources"].update(Panel(get_resource_table(), title="[bold white]ACTIVE RESOURCES[/]", border_style="blue"))
            
            # Read last few lines of log
            if LOG_FILE.exists():
                try:
                    # Simple tail implementation
                    with open(LOG_FILE, "r") as f:
                        lines = f.readlines()
                        last_lines = "".join(lines[-8:]) # Reduced log lines
                        current_status = Text(f"Tunnel PID: {pid}\n\n{last_lines}", style="green")
                        layout["logs"].update(Panel(current_status, title="Tunnel Logs", border_style="green"))
                except Exception:
                    pass
            
            frame_count += 1
            time.sleep(0.25)

@app.command()
def stop():
    """
    Stop the background tunnel process.
    """
    pid = is_tunnel_running()
    if not pid:
        console.print("[red]Tunnel is not running.[/red]")
        return
    
    try:
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Stopped tunnel process (PID: {pid}).[/green]")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        console.print(f"[red]Failed to stop tunnel: {e}[/red]")

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
    config_file = Path("config.yml")
    if config_file.exists():
        if Confirm.ask(f"Remove local configuration file ({config_file.absolute()})?"):
            try:
                config_file.unlink()
                console.print("[green]Configuration file removed.[/green]")
            except Exception as e:
                console.print(f"[red]Failed to remove config file: {e}[/red]")
    else:
        console.print("[yellow]No local configuration file found.[/yellow]")

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
