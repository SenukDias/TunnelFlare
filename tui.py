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
        padding: 1 2;
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    
    #title {
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    
    Input {
        margin-bottom: 1;
    }
    
    .buttons {
        width: 100%;
        height: auto;
        align: center bottom;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Add New DNS Record", id="title"),
            Label("Hostname (e.g., app.example.com):"),
            Input(placeholder="app.example.com", id="hostname"),
            Label("Local Service (e.g., http://localhost:8000):"),
            Input(placeholder="http://localhost:8000", id="service"),
            Horizontal(
                Button("Add", variant="primary", id="add"),
                Button("Cancel", variant="error", id="cancel"),
                classes="buttons"
            ),
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
    
    # Diagnostics
    internet_status = "checking" # checking, ok, error
    tunnel_status = "checking"
    local_status = "checking"
    log_status = "ok" # ok, warning, error
    
    def on_mount(self) -> None:
        self.fetch_ips()
        self.check_health()
        self.set_interval(0.2, self.refresh_topology) # Faster refresh for smooth animation
        self.set_interval(5, self.check_health) # Re-check health every 5s

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

    def check_log_errors(self):
        """Scan the last 20 lines of the log file for errors."""
        if not LOG_FILE.exists(): return "ok"
        try:
            with open(LOG_FILE, "r") as f:
                # Read last 2000 bytes approx
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 2000))
                lines = f.readlines()[-20:] # Last 20 lines
                
                for line in lines:
                    line_lower = line.lower()
                    if "err" in line_lower or "error" in line_lower or "failed" in line_lower or "terminated" in line_lower:
                        return "error"
                    if "warn" in line_lower or "retrying" in line_lower:
                        return "warning"
        except:
            pass
        return "ok"

    @work(thread=True)
    def check_health(self):
        # 1. Internet Check
        try:
            requests.get("https://1.1.1.1", timeout=2)
            self.internet_status = "ok"
        except:
            self.internet_status = "error"
            
        # 2. Tunnel Check (Process)
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                self.tunnel_status = "ok"
            except:
                self.tunnel_status = "error"
        else:
            self.tunnel_status = "stopped"
            
        # 3. Local Service Check (First one in config)
        self.local_status = "ok" # Default to OK if no service to check
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = yaml.safe_load(f)
                if "ingress" in config:
                    for rule in config["ingress"]:
                        service = rule.get("service", "")
                        if service.startswith("http"):
                            try:
                                requests.get(service, timeout=1)
                                self.local_status = "ok"
                                break
                            except:
                                self.local_status = "error"
            except:
                pass
        
        # 4. Log Check
        self.log_status = self.check_log_errors()

    def refresh_topology(self):
        self.update(self.generate_topology())

    def generate_topology(self):
        # Colors based on status
        color_internet = "green" if self.internet_status == "ok" else "red"
        color_tunnel = "green" if self.tunnel_status == "ok" else "red"
        if self.tunnel_status == "stopped": color_tunnel = "yellow"
        
        # Local status depends on Tunnel status too now
        if self.tunnel_status != "ok":
             # If tunnel is down, local is effectively isolated from the outside
             color_local = "yellow" 
             status_local_text = "Isolated"
        else:
             color_local = "green" if self.local_status == "ok" else "red"
             status_local_text = "Reachable" if self.local_status == "ok" else "Unreachable"

        # Log Status Effect
        if self.log_status == "error":
            color_tunnel = "red" # Override tunnel color on error
        elif self.log_status == "warning":
            color_tunnel = "yellow"

        # Retro Icons (Unicode Art)
        
        # Client (Retro PC)
        icon_client = Text.from_markup(f"""[cyan]
 ╔══════╗ 
 ║ >_   ║ 
 ╚╦════╦╝ 
  ╚════╝  
  CLIENT  [/cyan]""")

        # Internet (Retro Browser Window)
        icon_internet = Text.from_markup(f"""[{color_internet}]
 ╔══════╗ 
 ║ WWW  ║ 
 ║      ║ 
 ╚══════╝ 
 INTERNET [/]""")

        # Cloudflare (Retro Cloud)
        icon_cloudflare = Text.from_markup(f"""[bold {CLOUDFLARE_ORANGE}]
   _  _   
 (  )( )  
(______ ) 
          
CLOUDFLARE[/]""")

        # Tunnel (Retro Pipe/Gate)
        icon_tunnel = Text.from_markup(f"""[{color_tunnel}]
 ╔══════╗ 
 ║TUNNEL║ 
 ║>>>>>>║ 
 ╚══════╝ 
  TUNNEL  [/]""")

        # Localhost (Retro Server Rack)
        icon_local = Text.from_markup(f"""[{color_local}]
 ╔══════╗ 
 ║[||||]║ 
 ║[||||]║ 
 ╚══════╝ 
  SERVER  [/]""")

        # Connectivity Animation (Modern Retro Packet Flow)
        # Pattern: · · ● · · ● · ·
        t = int(time.time() * 10) # Fast ticker
        width = 10
        
        def get_flow_line(active=True, warning=False):
            if not active:
                return Text("──────────", style="dim white")
            
            chars = []
            for i in range(width):
                # Create a moving wave/packet effect
                if (i - t) % 4 == 0:
                    chars.append("●") # Packet
                else:
                    chars.append("·") # Trail
            
            line_str = "".join(chars)
            style = "bold red blink" if warning else "bold green"
            return Text.from_markup(f"\n\n[{style}]{line_str}[/]\n", justify="center")

        # Determine if flow is active based on health
        flow_internet = self.internet_status == "ok"
        flow_tunnel = self.tunnel_status == "ok"
        flow_local = self.local_status == "ok" and self.tunnel_status == "ok" # Local flow depends on tunnel
        
        # Warning state for lines
        warn_tunnel = self.log_status == "error"

        conn_1 = get_flow_line(flow_internet)
        conn_2 = get_flow_line(flow_internet and flow_tunnel, warning=warn_tunnel) 
        conn_3 = get_flow_line(flow_tunnel, warning=warn_tunnel)
        conn_4 = get_flow_line(flow_local)

        grid = Table.grid(expand=True, padding=0)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="center", ratio=1)

        grid.add_row(
            icon_client, conn_1, icon_internet, conn_2, icon_cloudflare, conn_3, icon_tunnel, conn_4, icon_local
        )
        
        # Status Text
        status_internet = "Connected" if self.internet_status == "ok" else "Disconnected"
        status_tunnel = "Active" if self.tunnel_status == "ok" else ("Stopped" if self.tunnel_status == "stopped" else "Error")
        
        # Append Log Status
        if self.log_status == "error":
            status_tunnel += " (Errors)"
        elif self.log_status == "warning":
            status_tunnel += " (Unstable)"

        # Details Row
        grid.add_row(
            Text("Client", style="dim cyan", justify="center"),
            "",
            Text.from_markup(f"Public IP:\n{self.public_ip}\n[{color_internet}]{status_internet}[/]", style="white", justify="center"),
            "",
            Text("Anycast\nNetwork", style=f"dim {CLOUDFLARE_ORANGE}", justify="center"),
            "",
            Text.from_markup(f"UUID:\n{self.tunnel_id}\n[{color_tunnel}]{status_tunnel}[/]", style="white", justify="center"),
            "",
            Text.from_markup(f"Local IP:\n{self.local_ip}\n[{color_local}]{status_local_text}[/]", style="white", justify="center")
        )

        return Panel(grid, title="[bold white]NETWORK DIAGNOSTICS[/]", border_style=CLOUDFLARE_ORANGE)

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
        ("r", "restart_tunnel", "Restart Tunnel"),
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
                yield Button("Start/Stop", id="btn_toggle", variant="warning")
                yield Button("Restart", id="btn_restart", variant="default")
        
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
        elif event.button.id == "btn_restart":
            self.restart_tunnel()

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
                # Use SIGINT for graceful shutdown (better for Cloudflare)
                os.kill(pid, signal.SIGINT)
                # Wait for process to die
                for _ in range(10): # Wait up to 5 seconds
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.5)
                    except OSError:
                        break # Process died
                
                if PID_FILE.exists(): PID_FILE.unlink()
                
                # Force immediate status update
                self.query_one(TopologyWidget).tunnel_status = "stopped"
                self.query_one(TopologyWidget).refresh_topology()
                self.check_tunnel_status() # Update button
                
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
            cred_file = config.get("credentials-file")
            
            if not tunnel_id:
                self.notify("No Tunnel ID found in config", severity="error")
                return
            
            if not cred_file:
                 self.notify("No Credentials File found in config", severity="error")
                 return

            if not Path(cred_file).exists():
                 self.notify(f"Credentials file missing: {cred_file}", severity="error")
                 self.notify("Please run 'tunnelflare reset' then 'setup'", severity="warning")
                 return

            TUNNEL_DIR.mkdir(exist_ok=True)
            
            cmd = [
                "cloudflared", 
                "tunnel", 
                "--config", str(CONFIG_FILE), 
                "--cred-file", str(cred_file),
                "run", 
                tunnel_id
            ]
            
            with open(LOG_FILE, "w") as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            with open(PID_FILE, "w") as f:
                f.write(str(process.pid))
            
            # Force immediate status update
            self.query_one(TopologyWidget).tunnel_status = "ok"
            self.query_one(TopologyWidget).refresh_topology()
            self.check_tunnel_status() # Update button
            
            self.notify(f"Tunnel Started (PID: {process.pid})")
            
        except Exception as e:
            self.notify(f"Failed to start: {e}", severity="error")

    def action_restart_tunnel(self):
        self.restart_tunnel()

    def restart_tunnel(self):
        self.notify("Restarting Tunnel...")
        # Stop if running
        if PID_FILE.exists():
            try:
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGINT) # Graceful
                # Wait for process to die
                for _ in range(10):
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.5)
                    except OSError:
                        break
                if PID_FILE.exists(): PID_FILE.unlink()
            except:
                pass
        
        # Start
        self.start_tunnel()

if __name__ == "__main__":
    app = TunnelFlareApp()
    app.run()
