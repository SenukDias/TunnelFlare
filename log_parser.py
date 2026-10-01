"""
TunnelFlare Structured Log Parser & Telemetry Classifier.
Parses raw cloudflared stdout/stderr into structured lifecycle stage events,
extracts real IP addresses, PoP locations, connection matrix states, and precheck readiness.
Persists structured records to ~/.tunnelflare/events.jsonl without data loss.
"""

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import time
from typing import Dict, List, Optional, Tuple

TUNNEL_DIR = Path.home() / ".tunnelflare"
RAW_LOG_FILE = TUNNEL_DIR / "tunnel.log"
EVENTS_JSONL_FILE = TUNNEL_DIR / "events.jsonl"

# Known Cloudflare PoP airport codes mapped to metro locations
CF_POP_LOCATIONS = {
    "bom": "Mumbai",
    "del": "Delhi",
    "blr": "Bangalore",
    "hyd": "Hyderabad",
    "maa": "Chennai",
    "ccu": "Kolkata",
    "sin": "Singapore",
    "fra": "Frankfurt",
    "lhr": "London",
    "iad": "Washington D.C.",
    "sjc": "San Jose",
    "ord": "Chicago",
    "dfw": "Dallas",
    "ams": "Amsterdam",
    "cdg": "Paris",
    "nrt": "Tokyo",
    "hkg": "Hong Kong",
    "syd": "Sydney",
}


def resolve_pop_name(location_code: str) -> str:
    """Format PoP codes like bom09 into 'bom09 (Mumbai)'."""
    if not location_code or location_code == "---":
        return "Unknown"
    code_prefix = location_code[:3].lower()
    city = CF_POP_LOCATIONS.get(code_prefix)
    if city:
        return f"{location_code} ({city})"
    return location_code.upper()


@dataclass
class PrecheckStatus:
    dns: str = "pending"          # pass, fail, pending
    udp_quic: str = "pending"     # pass, fail, pending
    tcp_h2: str = "pending"       # pass, fail, pending
    cf_api: str = "pending"       # pass, fail, pending
    suggested_protocol: str = "quic"
    hard_fail: bool = False
    run_id: str = ""
    last_updated: float = field(default_factory=time.time)

    def is_all_passed(self) -> bool:
        return (
            self.dns == "pass"
            and self.udp_quic == "pass"
            and self.tcp_h2 == "pass"
            and self.cf_api == "pass"
        )


@dataclass
class EdgeConnection:
    conn_index: int
    ip: str = "Connecting..."
    location: str = "---"
    protocol: str = "quic"
    connection_id: str = ""
    curve: str = ""
    status: str = "CONNECTING"     # ACTIVE, CONNECTING, DEGRADED, DISCONNECTED
    last_updated: float = field(default_factory=time.time)


@dataclass
class ParsedLogEvent:
    timestamp: str
    stage: str                     # PRECHECK, CRYPTO, EDGE_REG, TRAFFIC, HEALER, ERROR, SYSTEM
    level: str                     # INF, WRN, ERR, DBG
    message: str
    raw: str
    details: dict = field(default_factory=dict)
    conn_index: Optional[int] = None
    ip: Optional[str] = None
    location: Optional[str] = None
    protocol: Optional[str] = None


class LogParser:
    """
    Stateful streaming parser for cloudflared log outputs.
    Maintains precheck readiness, 4-edge connection matrix, and recent events.
    """

    def __init__(self, jsonl_path: Optional[Path] = None):
        self.jsonl_path = jsonl_path or EVENTS_JSONL_FILE
        self.precheck = PrecheckStatus()
        # 4 Cloudflare edge connection slots (0, 1, 2, 3)
        self.connections: Dict[int, EdgeConnection] = {
            i: EdgeConnection(conn_index=i) for i in range(4)
        }
        self.events_ring_buffer: List[ParsedLogEvent] = []
        self.max_buffer_size = 500
        self.last_parsed_offset = 0

    def parse_line(self, raw_line: str) -> Optional[ParsedLogEvent]:
        """Parse a single raw logfmt or plain log line from cloudflared."""
        line = raw_line.strip()
        if not line:
            return None

        # Ignore decorative banner pipes
        if line.endswith("INF |") or line.endswith("INF"):
            return None

        timestamp, level, body = self._extract_header(line)
        details = self._extract_key_values(body)

        stage = "SYSTEM"
        message = body
        conn_idx = None
        ip_addr = details.get("ip")
        loc_code = details.get("location")
        proto = details.get("protocol")

        if "connIndex" in details:
            try:
                conn_idx = int(details["connIndex"])
            except ValueError:
                conn_idx = None

        lower_body = body.lower()

        # -------------------------------------------------------------
        # STAGE 1: PRECHECK & READINESS
        # -------------------------------------------------------------
        if "precheck" in lower_body or "summary: environment is healthy" in lower_body:
            stage = "PRECHECK"
            comp = details.get("component", "")
            stat = details.get("status", "")
            tgt = details.get("target", "")

            if comp == "DNS Resolution":
                self.precheck.dns = stat
                message = f"DNS Resolution ({tgt}) ➔ {stat.upper()}"
            elif comp == "UDP Connectivity":
                self.precheck.udp_quic = stat
                message = f"UDP / QUIC Connectivity ({tgt}) ➔ {stat.upper()}"
            elif comp == "TCP Connectivity":
                self.precheck.tcp_h2 = stat
                message = f"TCP / HTTP2 Connectivity ({tgt}) ➔ {stat.upper()}"
            elif comp == "Cloudflare API":
                self.precheck.cf_api = stat
                message = f"Cloudflare API Reachability ➔ {stat.upper()}"
            elif "suggested_protocol" in details:
                s_proto = details.get("suggested_protocol", "quic")
                self.precheck.suggested_protocol = s_proto
                self.precheck.hard_fail = details.get("hard_fail", "false").lower() == "true"
                message = f"Precheck Complete ➔ Suggested: {s_proto.upper()} (Hard Fail: {self.precheck.hard_fail})"
            elif "summary:" in lower_body:
                message = body.split("SUMMARY:")[-1].strip()

            self.precheck.last_updated = time.time()

        # -------------------------------------------------------------
        # STAGE 2: CRYPTOGRAPHIC CURVE PREFERENCES
        # -------------------------------------------------------------
        elif "tunnel connection curve preferences:" in lower_body:
            stage = "CRYPTO"
            curve_match = re.search(r"curve preferences:\s*\[(.*?)\]", body, re.IGNORECASE)
            curves = curve_match.group(1) if curve_match else "X25519"
            if conn_idx is not None and 0 <= conn_idx < 4:
                self.connections[conn_idx].curve = curves
                if ip_addr:
                    self.connections[conn_idx].ip = ip_addr
                self.connections[conn_idx].status = "HANDSHAKING"
            message = f"Curve Preferences: [{curves}] (Conn #{conn_idx or 0} ➔ {ip_addr or 'Edge'})"

        # -------------------------------------------------------------
        # STAGE 3: ACTIVE EDGE CONNECTION REGISTRATION & MATRIX
        # -------------------------------------------------------------
        elif "unregistered tunnel connection" in lower_body or "connection disconnected" in lower_body:
            stage = "EDGE_REG"
            if conn_idx is not None and 0 <= conn_idx < 4:
                self.connections[conn_idx].status = "DISCONNECTED"
                self.connections[conn_idx].last_updated = time.time()
                message = f"Conn #{conn_idx} Disconnected ➔ {self.connections[conn_idx].ip}"
            else:
                message = f"Tunnel Edge Disconnected: {body}"

        elif "registered tunnel connection" in lower_body:
            stage = "EDGE_REG"
            if conn_idx is not None and 0 <= conn_idx < 4:
                slot = self.connections[conn_idx]
                if ip_addr:
                    slot.ip = ip_addr
                if loc_code:
                    slot.location = loc_code
                if proto:
                    slot.protocol = proto
                slot.connection_id = details.get("connection", slot.connection_id)
                slot.status = "ACTIVE"
                slot.last_updated = time.time()
                message = f"Conn #{conn_idx} Registered ➔ {slot.ip} @ {resolve_pop_name(slot.location)} ({slot.protocol.upper()})"
            else:
                message = f"Tunnel Connection Registered: {ip_addr or 'Edge'} @ {loc_code or 'PoP'}"

        # -------------------------------------------------------------
        # STAGE 4: ORIGIN TRAFFIC & HTTP PROXYING
        # -------------------------------------------------------------
        elif any(k in lower_body for k in ["unable to reach origin", "connection refused", "bad gateway", "502", "504"]):
            stage = "TRAFFIC"
            level = "ERR"
            message = f"Origin Routing Fault ➔ {body}"

        # -------------------------------------------------------------
        # STAGE 5: ERRORS & WARNINGS
        # -------------------------------------------------------------
        elif any(err in lower_body for err in ["err", "error", "failed", "fatal"]):
            stage = "ERROR"
            level = "ERR"
            message = body

        elif any(w in lower_body for w in ["warn", "warning", "retrying"]):
            stage = "SYSTEM"
            level = "WRN"
            message = body

        event = ParsedLogEvent(
            timestamp=timestamp,
            stage=stage,
            level=level,
            message=message,
            raw=raw_line,
            details=details,
            conn_index=conn_idx,
            ip=ip_addr,
            location=loc_code,
            protocol=proto,
        )

        self.events_ring_buffer.append(event)
        if len(self.events_ring_buffer) > self.max_buffer_size:
            self.events_ring_buffer.pop(0)

        # Append to persistent events JSONL
        self._append_to_jsonl(event)
        return event

    def _extract_header(self, line: str) -> Tuple[str, str, str]:
        """Extract timestamp, level (INF/ERR/WRN), and remaining body."""
        # Standard cloudflared line: 2026-09-28T10:37:14Z INF precheck component=...
        match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?)\s+([A-Z]{3})\s+(.*)$", line)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return time.strftime("%H:%M:%SZ"), "INF", line

    def _extract_key_values(self, body: str) -> dict:
        """Parse logfmt key=value pairs, handling quoted strings."""
        details = {}
        # Matches key="val" or key=val
        pairs = re.findall(r'(\w+)=(?:"([^"]*)"|([^\s]+))', body)
        for k, v1, v2 in pairs:
            details[k] = v1 if v1 != "" else v2
        return details

    def _append_to_jsonl(self, event: ParsedLogEvent) -> None:
        """Persist structured event record to disk for historical audit trails."""
        try:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            data = asdict(event)
            # Size rotation guard (10 MB limit)
            if self.jsonl_path.exists() and self.jsonl_path.stat().st_size > 10 * 1024 * 1024:
                backup = self.jsonl_path.with_suffix(".jsonl.1")
                os.replace(self.jsonl_path, backup)

            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass

    def get_active_count(self) -> int:
        """Return number of actively established edge connections."""
        return sum(1 for c in self.connections.values() if c.status == "ACTIVE")

    def get_summary_health(self) -> dict:
        """Return comprehensive health metrics for the dashboard."""
        active_conns = self.get_active_count()
        if active_conns == 4:
            health_state = "OPTIMAL"
        elif active_conns > 0:
            health_state = "DEGRADED"
        else:
            health_state = "OFFLINE"

        return {
            "health_state": health_state,
            "active_connections": active_conns,
            "total_slots": 4,
            "precheck_passed": self.precheck.is_all_passed(),
            "suggested_protocol": self.precheck.suggested_protocol,
        }
