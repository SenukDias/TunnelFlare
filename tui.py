from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, Button, DataTable, Log, Label, Input
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.layout import Layout
import yaml
import subprocess
import os
import signal
import time
import socket
import requests
from pathlib import Path

# Constants
TUNNEL_DIR = Path.home() / ".tunnelflare"
PID_FILE = TUNNEL_DIR / "tunnel.pid"
LOG_FILE = TUNNEL_DIR / "tunnel.log"
CONFIG_FILE = TUNNEL_DIR / "config.yml"
CLOUDFLARE_ORANGE = "#F38020"

class AddDNSScreen(ModalScreen):
    """Screen for adding a new DNS record."""
    
    CSS = """
    AddDNSScreen {
        align: center middle;
    }
    
    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        column-span: 2;
        height: 1;
        content-align: center middle;
        text-style: bold;
    }
    
    Label {
        column-span: 2;
    }
    
    Input {
        column-span: 2;
    }
    
    Button {
        width: 100%;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Add New DNS Record", id="title"),
            Label("Hostname (e.g., app.example.com):"),
            Input(placeholder="app.example.com", id="hostname"),
            Label("Local Service (e.g., http://localhost:8000):"),
            Input(placeholder="http://localhost:8000", id="service"),
            Button("Add", variant="primary", id="add"),
            Button("Cancel", variant="error", id="cancel"),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            hostname = self.query_one("#hostname", Input).value
            service = self.query_one("#service", Input).value
            if hostname and service:
                self.dismiss((hostname, service))
        else:
            self.dismiss(None)

    def action_cancel(self):
        self.dismiss(None)

class TopologyWidget(Static):
    """Widget to display the network topology."""
    
    public_ip = "Loading..."
    local_ip = "Loading..."
    tunnel_id = "Unknown"
    
    def on_mount(self) -> None:
        self.fetch_ips()
        self.set_interval(1, self.refresh_topology)

    @work(thread=True)
    def fetch_ips(self):
        # Fetch Public IP
        try:
            self.public_ip = requests.get("https://ifconfig.me", timeout=2).text.strip()
        except:
            self.public_ip = "Unavailable"
            
        # Fetch Local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.local_ip = s.getsockname()[0]
            s.close()
        except:
            self.local_ip = "127.0.0.1"
            
        # Get Tunnel ID from config
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = yaml.safe_load(f)
                    self.tunnel_id = config.get("tunnel", "Unknown")[:8] + "..."
            except:
                pass

    def refresh_topology(self):
        self.update(self.generate_topology())

    def generate_topology(self):
        # High Quality Block Art Icons
        
        icon_client = Text.from_markup(f"""[cyan]
   ▄████▄   
  ▐█▀  ▀█▌  
  ▐█    █▌  
  ▐█▄  ▄█▌  
   ▀████▀   
   CLIENT   [/cyan]""")

        icon_internet = Text.from_markup(f"""[white]
    ▄▄▄▄    
  ▄█▀  ▀█▄  
  █  {self.public_ip.center(4)}  █  
  ▀█▄  ▄█▀  
    ▀▀▀▀    
  INTERNET  [/white]""")

        icon_cloudflare = Text.from_markup(f"""[bold {CLOUDFLARE_ORANGE}]
     ▄▄▄     
   ▄█▀▀█▄   
  ▐█    █▌  
   ▀█▄▄█▀   
            
 CLOUDFLARE [/bold {CLOUDFLARE_ORANGE}]""")

        icon_tunnel = Text.from_markup(f"""[green]
   ▄████▄   
  ▐█    █▌  
  ▐█    █▌  
  ▐█    █▌  
   ▀████▀   
   TUNNEL   [/green]""")

        icon_local = Text.from_markup(f"""[yellow]
     ▄█▄     
   ▄█▀▀█▄   
  ▐█    █▌  
  ▐█▄▄▄▄█▌  
            
 LOCALHOST  [/yellow]""")

        # Connectivity Animation
        t = int(time.time() * 4) % 4
        arrow = " >>>"[t:] + " >>>"[:t]
        conn = Text(f"\n\n [bold green]{arrow}[/bold green] \n", justify="center")

        grid = Table.grid(expand=True, padding=1)
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")
        grid.add_column(justify="center")

        grid.add_row(
            icon_client, conn, icon_internet, conn, icon_cloudflare, conn, icon_tunnel, conn, icon_local
        )
        
        # Details Row
        grid.add_row(
            Text("IP: Detected", style="dim cyan", justify="center"),
            "",
            Text(f"Public IP:\n{self.public_ip}", style="bold white", justify="center"),
            "",
            Text("Anycast\nNetwork", style=f"dim {CLOUDFLARE_ORANGE}", justify="center"),
            "",
            Text(f"UUID:\n{self.tunnel_id}", style="dim green", justify="center"),
            "",
            Text(f"Local IP:\n{self.local_ip}", style="bold yellow", justify="center")
        )

        return Panel(grid, title="[bold white]NETWORK TOPOLOGY[/]", border_style=CLOUDFLARE_ORANGE)

class TunnelFlareApp(App):
    """The main TUI application."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-rows: 3fr 2fr;
        grid-columns: 1fr 1fr;
        grid-gutter: 1;
        padding: 1;
    }
    
    #topology {
        column-span: 2;
        height: 100%;
    }
    
    #resources {
        height: 100%;
        border: solid blue;
    }
    
    #logs {
        height: 100%;
        border: solid green;
    }
    
    .box {
        height: 100%;
        border: solid green;
    }
    
    DataTable {
        height: 1fr;
    }
    
    #controls {
        height: auto;
        dock: bottom;
        layout: horizontal;
        align: center middle;
        padding: 1;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_dns", "Add DNS"),
        ("s", "toggle_tunnel", "Start/Stop Tunnel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield TopologyWidget(id="topology")
        
        with Container(id="resources"):
            yield Label("[bold white]ACTIVE RESOURCES[/]")
            yield DataTable(id="resource_table")
            with Horizontal(id="controls"):
                yield Button("Add DNS", id="btn_add", variant="primary")
                yield Button("Remove Selected", id="btn_remove", variant="error")
                yield Button("Start/Stop Tunnel", id="btn_toggle", variant="warning")
        
        with Container(id="logs"):
            yield Label("[bold white]TUNNEL LOGS[/]")
            yield Log(id="log_view")
            
        yield Footer()

    def on_mount(self) -> None:
        self.title = "TunnelFlare Dashboard"
        self.refresh_resources()
        self.set_interval(1, self.update_logs)
        self.set_interval(2, self.check_tunnel_status)

    def refresh_resources(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Hostname", "Service", "Status")
        table.cursor_type = "row"
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = yaml.safe_load(f)
                    if "ingress" in config:
                        for rule in config["ingress"]:
                            hostname = rule.get("hostname", "*")
                            service = rule.get("service", "N/A")
                            if service == "http_status:404": continue
                            table.add_row(hostname, service, "Active")
            except:
                pass

    def update_logs(self):
        log_view = self.query_one(Log)
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, "r") as f:
                    # Read new lines only - simplified for now by just reading last 1KB
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 2000))
                    lines = f.read()
                    log_view.clear()
                    log_view.write(lines)
            except:
                pass

    def check_tunnel_status(self):
        # Check if tunnel is running
        is_running = False
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                is_running = True
            except:
                pass
        
        btn = self.query_one("#btn_toggle", Button)
        if is_running:
            btn.label = "Stop Tunnel"
            btn.variant = "error"
        else:
            btn.label = "Start Tunnel"
            btn.variant = "success"

    def action_add_dns(self):
        def check_add(result):
            if result:
                hostname, service = result
                self.add_dns_record(hostname, service)
                
        self.push_screen(AddDNSScreen(), check_add)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_add":
            self.action_add_dns()
        elif event.button.id == "btn_remove":
            self.remove_selected_dns()
        elif event.button.id == "btn_toggle":
            self.toggle_tunnel()

    def add_dns_record(self, hostname, service):
        if not CONFIG_FILE.exists(): return
        
        try:
            with open(CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
            
            # Insert before the 404 rule
            new_rule = {"hostname": hostname, "service": service}
            if "ingress" in config:
                config["ingress"].insert(-1, new_rule)
            else:
                config["ingress"] = [new_rule]
                
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(config, f, sort_keys=False)
                
            # Restart tunnel to apply changes
            self.restart_tunnel()
            self.refresh_resources()
            self.notify(f"Added {hostname} -> {service}")
            
        except Exception as e:
            self.notify(f"Error adding DNS: {e}", severity="error")

    def remove_selected_dns(self):
        table = self.query_one(DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if not row_key: return
        
        row = table.get_row(row_key)
        hostname_to_remove = row[0]
        
        if not CONFIG_FILE.exists(): return
        
        try:
            with open(CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
            
            if "ingress" in config:
                config["ingress"] = [r for r in config["ingress"] if r.get("hostname") != hostname_to_remove]
                
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(config, f, sort_keys=False)
                
            self.restart_tunnel()
            self.refresh_resources()
            self.notify(f"Removed {hostname_to_remove}")
            
        except Exception as e:
            self.notify(f"Error removing DNS: {e}", severity="error")

    def toggle_tunnel(self):
        is_running = False
        pid = None
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                is_running = True
            except:
                pass
        
        if is_running:
            # Stop
            try:
                os.kill(pid, signal.SIGTERM)
                if PID_FILE.exists(): PID_FILE.unlink()
                self.notify("Tunnel Stopped")
            except Exception as e:
                self.notify(f"Failed to stop: {e}", severity="error")
        else:
            # Start
            self.start_tunnel()

    def start_tunnel(self):
        if not CONFIG_FILE.exists(): return
        
        try:
            with open(CONFIG_FILE, "r") as f:
                config = yaml.safe_load(f)
            tunnel_id = config.get("tunnel")
            
            if not tunnel_id:
                self.notify("No Tunnel ID found in config", severity="error")
                return
                
            TUNNEL_DIR.mkdir(exist_ok=True)
            with open(LOG_FILE, "w") as log:
                process = subprocess.Popen(
                    ["cloudflared", "tunnel", "run", tunnel_id],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            with open(PID_FILE, "w") as f:
                f.write(str(process.pid))
                
            self.notify(f"Tunnel Started (PID: {process.pid})")
            
        except Exception as e:
            self.notify(f"Failed to start: {e}", severity="error")

    def restart_tunnel(self):
        # Simple restart if running
        if PID_FILE.exists():
            self.toggle_tunnel() # Stop
            time.sleep(1)
            self.toggle_tunnel() # Start

if __name__ == "__main__":
    app = TunnelFlareApp()
    app.run()
