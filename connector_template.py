
# Docker Compose with Dashboard Sidecar
WARP_CONNECTOR_COMPOSE = """version: '3'
services:
  warp-connector:
    image: cloudflare/cloudflared:latest
    container_name: warp_connector
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    volumes:
      - ./cloudflared:/etc/cloudflared
    command: tunnel run --metrics 0.0.0.0:44444
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    networks:
      warp_net:
        ipv4_address: 10.0.0.2

  dashboard:
    image: python:3.9-slim
    container_name: warp_dashboard
    restart: unless-stopped
    volumes:
      - ./dashboard:/app
    working_dir: /app
    ports:
      - "8080:8080"
    command: python3 server.py
    networks:
      warp_net:

networks:
  warp_net:
    ipam:
      config:
        - subnet: 10.0.0.0/24
"""

# Simple Python Server to bridge metrics or just serve static
DASHBOARD_SERVER = """
import http.server
import socketserver
import urllib.request
import json
import time

PORT = 8080
METRICS_URL = "http://10.0.0.2:44444/metrics"

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Try to fetch metrics from cloudflared
            status = {"connected": False, "uptime": 0, "bytes_in": 0, "bytes_out": 0}
            try:
                with urllib.request.urlopen(METRICS_URL, timeout=1) as response:
                     data = response.read().decode('utf-8')
                     status["connected"] = True
                     # Parse simple metrics if needed, for now just connectivity check
                     # In a real impl we'd regex parse Prometheus format
                     status["raw_metrics"] = data[:200] + "..." 
            except Exception as e:
                status["error"] = str(e)
                
            self.wfile.write(json.dumps(status).encode())
            return

        super().do_GET()

print(f"Serving Retro Dashboard on port {PORT}")
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
"""

# Retro HTML/CSS/JS
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>TunnelFlare // Connector</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');
        
        :root {
            --bg: #0d0d0d;
            --glass: rgba(20, 20, 20, 0.8);
            --neon-green: #39ff14;
            --neon-orange: #F38020;
            --dim-gray: #444;
        }

        body {
            background-color: var(--bg);
            color: var(--neon-green);
            font-family: 'VT323', monospace;
            margin: 0;
            padding: 20px;
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
                linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            background-size: 100% 2px, 3px 100%;
        }

        /* Scanline Effect */
        body::before {
            content: " ";
            display: block;
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
            z-index: 2;
            background-size: 100% 2px, 3px 100%;
            pointer-events: none;
        }
        
        /* Flicker */
        @keyframes flicker {
            0% { opacity: 0.97; }
            5% { opacity: 0.95; }
            10% { opacity: 0.9; }
            15% { opacity: 0.95; }
            20% { opacity: 0.99; }
            50% { opacity: 0.95; }
            55% { opacity: 0.9; }
            60% { opacity: 0.95; }
            100% { opacity: 0.98; }
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            width: 100%;
            border: 2px solid var(--neon-orange);
            padding: 2px;
            box-shadow: 0 0 15px var(--neon-orange);
            animation: flicker 0.15s infinite;
        }

        header {
            background: var(--neon-orange);
            color: black;
            padding: 10px;
            font-size: 2em;
            text-align: center;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 5px;
        }

        .main-display {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            padding: 20px;
            background: rgba(0,0,0,0.8);
        }

        .panel {
            border: 1px solid var(--neon-green);
            padding: 15px;
            box-shadow: inset 0 0 10px rgba(57, 255, 20, 0.2);
        }

        h2 {
            border-bottom: 1px dashed var(--neon-green);
            margin-top: 0;
        }

        .status-huge {
            font-size: 4em;
            text-align: center;
            margin: 20px 0;
            text-shadow: 0 0 10px var(--neon-green);
        }

        .log-box {
            grid-column: span 2;
            height: 200px;
            border: 1px dotted var(--dim-gray);
            font-family: monospace;
            padding: 10px;
            color: #aaa;
            overflow-y: auto;
            font-size: 0.9em;
        }

        .blink { animation: blink 1s step-end infinite; }
        @keyframes blink { 50% { opacity: 0; } }

        .btn {
            background: transparent;
            border: 2px solid var(--neon-green);
            color: var(--neon-green);
            padding: 10px 20px;
            font-family: inherit;
            font-size: 1.2em;
            cursor: pointer;
            text-transform: uppercase;
        }
        .btn:hover {
            background: var(--neon-green);
            color: black;
        }

    </style>
</head>
<body>
    <div class="container">
        <header>TunnelFlare Connector V.1.0</header>
        
        <div class="main-display">
            <!-- STATUS -->
            <div class="panel">
                <h2>SYSTEM STATUS</h2>
                <div id="status-text" class="status-huge">INITIALIZING...</div>
                <div style="text-align: center">
                    VPN NODE: <span style="color:white">ACTIVE</span><br>
                    ENCRYPTION: <span style="color:white">AES-256</span>
                </div>
            </div>

            <!-- METRICS -->
            <div class="panel">
                <h2>TELEMETRY</h2>
                <p>UPTIME: <span id="uptime">00:00:00</span></p>
                <p>PACKETS RX: <span id="rx" class="blink">...</span></p>
                <p>PACKETS TX: <span id="tx" class="blink">...</span></p>
                <p>LATENCY: <span style="color: var(--neon-orange)"> < 20ms </span></p>
            </div>

            <!-- LOGS -->
            <div class="panel log-box" id="log-box">
                > SYSTEM BOOT SEQ COMPLETE<br>
                > LOADED: CLOUDFLARED DRIVER<br>
                > TUNNELFLARE EXTENSION LOADED<br>
            </div>
        </div>
        
        <div style="text-align: center; padding: 10px;">
            <button class="btn" onclick="location.reload()">REFRESH SYSTEM</button>
        </div>
    </div>

    <script>
        const statusEl = document.getElementById('status-text');
        const logBox = document.getElementById('log-box');
        
        function log(msg) {
            const line = document.createElement('div');
            line.textContent = `> ${msg}`;
            logBox.appendChild(line);
            logBox.scrollTop = logBox.scrollHeight;
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                
                if (data.connected) {
                    statusEl.textContent = "ONLINE";
                    statusEl.style.color = "var(--neon-green)";
                    statusEl.style.textShadow = "0 0 20px var(--neon-green)";
                    log("HEARTBEAT: OK");
                } else {
                     statusEl.textContent = "OFFLINE";
                     statusEl.style.color = "red";
                     statusEl.style.textShadow = "0 0 20px red";
                     log("HEARTBEAT: TIMEOUT (Check Connector)");
                }
            } catch (e) {
                statusEl.textContent = "ERROR";
                statusEl.style.color = "orange";
                log("CONNECTION ERROR: " + e);
            }
        }

        setInterval(fetchStatus, 3000);
        setTimeout(fetchStatus, 500);
    </script>
</body>
</html>
"""
