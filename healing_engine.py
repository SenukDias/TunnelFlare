"""
TunnelFlare Autonomous Self-Healing Engine (AIOps).
Monitors precheck state, 4-edge connection health, and log events to execute
remediation playbooks (protocol fallback to HTTP/2, edge reconnection, circuit breaker).
"""

from dataclasses import dataclass, field
import enum
import logging
from pathlib import Path
import time
import threading
import subprocess
import requests
import yaml
from typing import Callable, List, Optional

from log_parser import LogParser, ParsedLogEvent

TUNNEL_DIR = Path.home() / ".tunnelflare"
CONFIG_FILE = TUNNEL_DIR / "config.yml"


class HealthFSMState(str, enum.Enum):
    STOPPED = "STOPPED"
    PRECHECKING = "PRECHECKING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    HEALING = "HEALING"
    CIRCUIT_TRIPPED = "CIRCUIT_TRIPPED"


@dataclass
class HealingActionRecord:
    timestamp: float
    trigger: str
    action_taken: str
    status: str       # SUCCESS, FAILED, THROTTLED
    details: str = ""


class HealingEngine:
    """
    Finite State Machine and Automated Remediation Controller.
    Implements a resilient circuit breaker, backoff curves, and playbooks.
    """

    MAX_ACTIONS_PER_WINDOW = 3
    WINDOW_SECONDS = 300       # 5 minutes
    COOLDOWN_SECONDS = 25       # Minimum gap between actions

    def __init__(
        self,
        parser: LogParser,
        restart_callback: Optional[Callable[[dict], bool]] = None,
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.parser = parser
        self.restart_callback = restart_callback
        self.notify_callback = notify_callback
        self.is_armed = True
        self.state = HealthFSMState.STOPPED
        self.action_history: List[HealingActionRecord] = []
        self.last_action_time = 0.0
        self.active_protocol = "quic"
        self.quic_failure_count = 0
        self.circuit_tripped = False
        self.trip_reason = ""
        
        # Start the background watchdog thread for smart auto-fix
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def set_armed(self, armed: bool) -> None:
        """Toggle autonomous healing mode."""
        self.is_armed = armed

    def trip_circuit_breaker(self, reason: str) -> None:
        """Lock out further automated interventions to protect system/API."""
        self.circuit_tripped = True
        self.trip_reason = reason
        self.state = HealthFSMState.CIRCUIT_TRIPPED
        if self.notify_callback:
            self.notify_callback(f"Circuit Breaker TRIPPED: {reason}", "error")

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker."""
        self.circuit_tripped = False
        self.trip_reason = ""
        self.action_history.clear()
        self.state = HealthFSMState.HEALTHY
        if self.notify_callback:
            self.notify_callback("Circuit Breaker reset. Autonomous healing re-armed.", "information")

    def _can_execute_action(self) -> bool:
        """Check rate-limit circuit breaker: max 3 actions in 5 min window."""
        now = time.time()
        if not self.is_armed:
            return False
        if self.circuit_tripped:
            return False
        if (now - self.last_action_time) < self.COOLDOWN_SECONDS:
            return False

        # Clean old actions from sliding window
        recent_actions = [a for a in self.action_history if (now - a.timestamp) < self.WINDOW_SECONDS]
        if len(recent_actions) >= self.MAX_ACTIONS_PER_WINDOW:
            self.trip_circuit_breaker(
                f"Rate limit exceeded: {len(recent_actions)} actions in 5 min. Manual review required."
            )
            return False

        return True

    def evaluate_health(self, tunnel_running: bool) -> HealthFSMState:
        """Evaluate overall health state based on parser metrics."""
        if not tunnel_running:
            self.state = HealthFSMState.STOPPED
            return self.state

        if self.circuit_tripped:
            self.state = HealthFSMState.CIRCUIT_TRIPPED
            return self.state

        precheck = self.parser.precheck
        active_conns = self.parser.get_active_count()

        if not precheck.is_all_passed() and precheck.dns == "pending":
            self.state = HealthFSMState.PRECHECKING
            return self.state

        if active_conns == 4 and precheck.is_all_passed():
            self.state = HealthFSMState.HEALTHY
            self.quic_failure_count = 0
            return self.state

        if active_conns > 0 or precheck.is_all_passed():
            self.state = HealthFSMState.DEGRADED
            return self.state

        self.state = HealthFSMState.DEGRADED
        return self.state

    def process_event(self, event: ParsedLogEvent, tunnel_running: bool) -> Optional[HealingActionRecord]:
        """Inspect streaming log event for fault signatures and trigger remediation."""
        if not tunnel_running:
            return None

        lower_msg = event.message.lower()
        
        with open("/tmp/healer_debug.log", "a") as f:
            f.write(f"process_event: {event.message}\n")
            f.write(f"active_protocol: {self.active_protocol}, is_armed: {self.is_armed}\n")

        # -------------------------------------------------------------
        # SIGNATURE 1: AUTHENTICATION / TOKEN REVOCATION (FATAL)
        # -------------------------------------------------------------
        if any(k in lower_msg for k in ["unauthorized", "invalid token", "authentication error"]):
            self.trip_circuit_breaker("Cloudflare Token Invalid / Revoked. Stopping tunnel restart loops.")
            record = HealingActionRecord(
                timestamp=time.time(),
                trigger="AUTH_FAILURE",
                action_taken="TRIP_CIRCUIT_BREAKER",
                status="SUCCESS",
                details="Authentication failed; halted automated loops to prevent account lock.",
            )
            self.action_history.append(record)
            return record

        # -------------------------------------------------------------
        # SIGNATURE 2: UDP / QUIC FAILURE (FALLBACK TO HTTP/2)
        # -------------------------------------------------------------
        is_quic_fail = (
            (event.stage == "PRECHECK" and "UDP / QUIC Connectivity" in event.message and "FAIL" in event.message)
            or ("quic: timeout" in lower_msg)
            or ("failed to dial a quic connection" in lower_msg)
            or ("quic connection failed" in lower_msg)
        )

        if is_quic_fail and self.active_protocol == "quic":
            self.parser.precheck.udp = "fail"
            self.quic_failure_count += 1
            if self.quic_failure_count >= 1 and self._can_execute_action():
                return self._execute_protocol_switch("http2", "UDP_QUIC_FAIL", "Switched protocol from QUIC to HTTP/2 due to UDP packet loss / firewall block.")

        # -------------------------------------------------------------
        # SIGNATURE 4: HTTP/2 FAILURE (FALLBACK TO QUIC)
        # -------------------------------------------------------------
        is_h2_fail = (
            (event.stage == "PRECHECK" and "TCP Connectivity" in event.message and "FAIL" in event.message)
            or ("failed to dial to edge with h2" in lower_msg)
            or ("failed to dial a h2 connection" in lower_msg)
            or ("http2 connection failed" in lower_msg)
            or ("dial tcp" in lower_msg and "connection refused" in lower_msg and "edge" in lower_msg)
        )

        if is_h2_fail and self.active_protocol == "http2":
            self.parser.precheck.tcp = "fail"
            if self._can_execute_action():
                return self._execute_protocol_switch("quic", "TCP_H2_FAIL", "Switched protocol from HTTP/2 to QUIC due to TCP/H2 failure.")

        # -------------------------------------------------------------
        # SIGNATURE 5: QUIC RECOVERY (UPGRADE TO QUIC)
        # -------------------------------------------------------------
        is_quic_pass = (
            event.stage == "PRECHECK" and "UDP / QUIC Connectivity" in event.message and "PASS" in event.message
        )

        if is_quic_pass and self.active_protocol == "http2":
            if self._can_execute_action():
                return self._execute_protocol_switch("quic", "QUIC_RECOVERY", "Upgraded protocol from HTTP/2 back to QUIC (UDP connectivity restored).")

        # -------------------------------------------------------------
        # SIGNATURE 3: TOTAL EDGE DISCONNECTION (ALL 4 CONNS LOST)
        # -------------------------------------------------------------
        if event.stage == "EDGE_REG" and "disconnected" in lower_msg:
            active_conns = self.parser.get_active_count()
            if active_conns == 0 and self._can_execute_action():
                return self._execute_mesh_reconnect(trigger="TOTAL_EDGE_DROP")

        return None

    def _execute_protocol_switch(self, target_protocol: str, trigger: str, action_msg: str) -> HealingActionRecord:
        """Remediation Playbook: Switch active protocol and restart."""
        self.state = HealthFSMState.HEALING
        self.last_action_time = time.time()
        self.active_protocol = target_protocol

        success = False

        if self.restart_callback:
            success = self.restart_callback({"protocol": target_protocol})

        record = HealingActionRecord(
            timestamp=self.last_action_time,
            trigger=trigger,
            action_taken=f"PROTOCOL_FALLBACK_{target_protocol.upper()}",
            status="SUCCESS" if success else "FAILED",
            details=action_msg,
        )
        self.action_history.append(record)

        if self.notify_callback:
            severity = "warning" if success else "error"
            self.notify_callback(f"Auto-Heal: {action_msg}", severity)

        # Record healer event in log parser
        self.parser.parse_line(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} INF [HEALER] {action_msg} Status: {'APPLIED' if success else 'FAILED'}"
        )
        return record

    def _execute_mesh_reconnect(self, trigger: str) -> HealingActionRecord:
        """Remediation Playbook 2: Soft restart/reconnect tunnel when all edge connections drop."""
        self.state = HealthFSMState.HEALING
        self.last_action_time = time.time()
        
        # Reset to primary protocol (QUIC) on any full mesh reconnect
        self.active_protocol = "quic"
        action_msg = f"Initiating edge re-establishment sequence using QUIC (Trigger: {trigger})."
        success = False

        if self.restart_callback:
            success = self.restart_callback({"protocol": self.active_protocol})

        record = HealingActionRecord(
            timestamp=self.last_action_time,
            trigger=trigger,
            action_taken="EDGE_RECONNECT_RESTART",
            status="SUCCESS" if success else "FAILED",
            details=action_msg,
        )
        self.action_history.append(record)

        if self.notify_callback:
            self.notify_callback(f"Auto-Heal: {action_msg}", "warning" if success else "error")

        self.parser.parse_line(
            f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} INF [HEALER] {action_msg}"
        )
        return record

    def get_healer_status(self) -> dict:
        """Return diagnostic metrics for the TUI HUD."""
        recent_actions = [a for a in self.action_history if (time.time() - a.timestamp) < self.WINDOW_SECONDS]
        last_action = self.action_history[-1] if self.action_history else None

        return {
            "is_armed": self.is_armed,
            "fsm_state": self.state.value,
            "circuit_tripped": self.circuit_tripped,
            "trip_reason": self.trip_reason,
            "active_protocol": self.active_protocol,
            "actions_in_window": len(recent_actions),
            "max_actions": self.MAX_ACTIONS_PER_WINDOW,
            "last_action_str": (
                f"{last_action.action_taken} ({last_action.status})" if last_action else "None (Nominal)"
            ),
        }

    def _watchdog_loop(self):
        """Background thread running sensors for smart auto-fix."""
        last_http_probe = 0
        while True:
            time.sleep(5)
            if not self.is_armed or self.state == HealthFSMState.STOPPED:
                continue

            try:
                tunnel_id = None
                if CONFIG_FILE.exists():
                    with open(CONFIG_FILE, "r") as f:
                        cfg = yaml.safe_load(f)
                        if cfg:
                            tunnel_id = cfg.get("tunnel")
                
                if tunnel_id:
                    # Sensor A: Ghost Process Detector
                    cmd = f"pgrep -f 'cloudflared tunnel.*run {tunnel_id}'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    pids = [p for p in result.stdout.strip().split("\n") if p]
                    if len(pids) > 1:
                        self._execute_smart_autofix("GHOST_PROCESS_CONFLICT", tunnel_id)
                        continue 

                    # Sensor B: Synthetic Edge Probing
                    now = time.time()
                    if now - last_http_probe > 60:
                        last_http_probe = now
                        if self.state == HealthFSMState.HEALTHY:
                            endpoints = []
                            if cfg and "ingress" in cfg:
                                for rule in cfg["ingress"]:
                                    host = rule.get("hostname", "*")
                                    if host != "*" and not host.endswith("[Site-to-Site]"):
                                        endpoints.append(f"https://{host}")
                            
                            desync_detected = False
                            for ep in endpoints:
                                try:
                                    resp = requests.head(ep, timeout=5)
                                    if resp.status_code == 530:
                                        desync_detected = True
                                        break
                                except Exception:
                                    pass
                            
                            if desync_detected:
                                self._execute_smart_autofix("EDGE_DESYNC", tunnel_id)
            except Exception as e:
                with open("/tmp/healer_debug.log", "a") as f:
                    f.write(f"Ghost process watchdog error: {e}\n")

    def _execute_smart_autofix(self, trigger: str, tunnel_id: str) -> None:
        """Remediation Playbook for Ghost Processes and Edge Desync."""
        if not self._can_execute_action():
            return
            
        self.state = HealthFSMState.HEALING
        self.last_action_time = time.time()
        
        action_msg = f"Smart Auto-Fix Executing: {trigger} detected."
        if self.notify_callback:
            self.notify_callback(f"Auto-Heal: {action_msg}", "warning")
            
        try:
            # 1. Nuclear Termination
            subprocess.run(f"pkill -9 -f 'cloudflared tunnel.*{tunnel_id}'", shell=True)
            time.sleep(1)
            
            # 2. DNS State Sync
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    cfg = yaml.safe_load(f)
                    if cfg and "ingress" in cfg:
                        for rule in cfg["ingress"]:
                            host = rule.get("hostname", "*")
                            if host != "*" and not host.endswith("[Site-to-Site]"):
                                subprocess.run(
                                    ["cloudflared", "tunnel", "route", "dns", "--overwrite-dns", tunnel_id, host],
                                    check=False,
                                    capture_output=True
                                )
                                
            # 3. Clean Boot
            success = False
            if self.restart_callback:
                self.active_protocol = "quic"
                success = self.restart_callback({"protocol": self.active_protocol})
                
            record = HealingActionRecord(
                timestamp=self.last_action_time,
                trigger=trigger,
                action_taken="SMART_AUTO_FIX_RESTART",
                status="SUCCESS" if success else "FAILED",
                details=action_msg,
            )
            self.action_history.append(record)
            
            self.parser.parse_line(
                f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} INF [HEALER] {action_msg} Status: {'APPLIED' if success else 'FAILED'}"
            )
            
        except Exception as e:
            with open("/tmp/healer_debug.log", "a") as f:
                f.write(f"Smart autofix error: {e}\n")
