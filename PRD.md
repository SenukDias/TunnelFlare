# Product Requirements Document (PRD)
## TunnelFlare v2.1: Intelligent Log Observability & Autonomous Healing Model

---

## 1. Overview & Problem Statement

### 1.1 Context
TunnelFlare is an enterprise-grade Cloudflare Tunnel and Zero Trust Mesh orchestrator providing both a modern web application and an interactive terminal TUI HUD. Currently, the TUI's live log viewer streams raw stdout/stderr text directly from the `cloudflared` daemon into a generic RichLog widget.

### 1.2 Problem Statement
- **Information Overload & Noise**: Raw `cloudflared` logs mingle precheck diagnostics, cryptographic curve preferences, Anycast edge connections, protocol negotiations, and traffic events in unstructured logfmt strings.
- **Obscured High-Value Telemetry**: Critical data such as public Anycast IP addresses (`2606:4700:a0::5`), Cloudflare PoP location codes (`bom09`, `sin02`, `fra15`), connection slots (`connIndex=0..3`), and precheck statuses are buried within verbose text.
- **Lack of Operational Lifecycle Stages**: Operators cannot ascertain whether a tunnel is currently in pre-flight checks, negotiating cryptographic handshakes, maintaining active edge mesh connections, or experiencing transient degradations.
- **Absence of Autonomous Self-Healing**: When standard connection anomalies occur (e.g., local firewalls blocking UDP/QUIC, edge node flapping, or origin service outages), the system prints errors without taking automated corrective actions.

---

## 2. Product Goals & Scope

1. **Structured Log Ingestion & Zero-Data-Loss Storage**:
   - Preserve 100% of the raw `cloudflared` stdout/stderr stream in `~/.tunnelflare/tunnel.log` (with size-based rotation).
   - Ingest and parse logs into typed structured events, writing persistent audit records to `~/.tunnelflare/events.jsonl`.
2. **5-Stage Operational Lifecycle Model**:
   - Categorize all events and system states across 5 explicit stages:
     1. Pre-Flight Readiness (DNS, UDP, TCP, Cloudflare API)
     2. Cryptographic & Protocol Negotiation (Curves, QUIC vs. HTTP/2)
     3. Active Edge Mesh Matrix (4 concurrent Anycast connections, PoP codes, IPs, status)
     4. Ingress & Origin Route Proxying (Target service reachability, HTTP status codes)
     5. Autonomous Fault Detection & Healing
3. **High-Density Split-Deck TUI Observability**:
   - Transform the right-hand TUI workspace into a high-density, two-tier HUD:
     - **Upper Deck**: Active 4-Edge Connection Grid and Precheck Readiness Status Pills.
     - **Lower Deck**: Clean, stage-categorized log stream with color-coded badges, highlighted IPs, and stripped noise.
     - **Instant Raw Toggle**: Hotkey (`[Tab]` or `[V]`) to toggle between the curated stream and the raw daemon output.
4. **Autonomous Self-Healing Model (AIOps Engine)**:
   - Implement an event-driven Finite State Machine (FSM) with automated remediation playbooks:
     - Automatic protocol downgrade (QUIC ➔ HTTP/2) if UDP is dropped by firewalls/ISPs.
     - Soft reconnection for stale or dropped edge connections.
     - Upstream DNS fallback for resolver failures.
     - Origin isolation alerting (distinguishing origin crashes from tunnel drops).
   - Safety Circuit Breaker: Max 3 auto-remediations per 5 minutes with exponential backoff.

---

## 3. System Architecture & Components

```
                     ┌──────────────────────────────────────────────┐
                     │              cloudflared Daemon              │
                     └──────────────────────┬───────────────────────┘
                                            │ stdout / stderr
                                            ▼
                          ┌───────────────────────────────────┐
                          │   Log Persistence & Dual Store    │
                          │   (~/.tunnelflare/tunnel.log)     │
                          └─────────────────┬─────────────────┘
                                            │ Streaming Read
                                            ▼
                          ┌───────────────────────────────────┐
                          │   Structured Stream Parser        │
                          │   (log_parser.py)                 │
                          └─────────┬───────────────────┬─────┘
                                    │                   │
                        Parsed Events                   │ Append to
                                    ▼                   ▼
                      ┌──────────────────────┐  ┌─────────────────────────┐
                      │ Reactive State Store │  │ ~/.tunnelflare/         │
                      │ (Precheck, 4-Conns,  │  │ events.jsonl            │
                      │  Diagnostics)        │  └─────────────────────────┘
                      └──────────┬───────────┘
                                 │
             ┌───────────────────┴──────────────────┐
             ▼                                      ▼
┌───────────────────────────────┐      ┌───────────────────────────────┐
│     Automated Healing Engine  │      │     Textual TUI Modern HUD    │
│     (healing_engine.py)       │      │     (tui.py)                  │
│  - Anomaly Detection Rules    │      │  - Top: 4-Edge Matrix Grid    │
│  - Playbook Remediation       │      │  - Top: Pre-Flight Pills      │
│  - Circuit Breaker Guardrail  │      │  - Bottom: Curated Log Stream │
└────────────┬──────────────────┘      │  - [Tab/V]: Raw Logs Toggle   │
             │ Actions                 └───────────────────────────────┘
             ▼
┌───────────────────────────────┐
│ Subprocess / Protocol Manager │
└───────────────────────────────┘
```

---

## 4. Detailed Component Specifications

### 4.1 Log Parsing & Data Pipeline (`log_parser.py`)

#### Supported Log Patterns:
1. **Pre-flight Checks**:
   - Format: `precheck component="<Component>" details="<Details>" run_id=<UUID> status=<pass|fail> target=<Target>`
   - Extracted fields: `component` (DNS Resolution, UDP Connectivity, TCP Connectivity, Cloudflare API), `status`, `target`, `details`.
2. **Protocol & Suggested Protocol**:
   - Format: `precheck complete hard_fail=<bool> suggested_protocol=<quic|http2>`
   - Format: `SUMMARY: Environment is healthy. cloudflared will use '<protocol>' as primary protocol.`
3. **Curve Preferences**:
   - Format: `Tunnel connection curve preferences: [<Curves>] connIndex=<N> event=<N> ip=<IP>`
4. **Edge Connection Registration**:
   - Format: `Registered tunnel connection connIndex=<0..3> connection=<UUID> event=0 ip=<IP> location=<PoP> protocol=<quic|http2>`
   - Extracted fields: `conn_index`, `connection_id`, `ip` (IPv4 or IPv6), `location` (e.g. `bom09`), `protocol`.
5. **Connection Unregistration / Disconnection**:
   - Format: `Unregistered tunnel connection connIndex=<0..3> ...` or `Connection <UUID> disconnected ...`
6. **Origin Errors / HTTP Proxying**:
   - Format: `ERR Unable to establish connection with origin ... dial tcp 127.0.0.1:<port>: connect: connection refused`

#### In-Memory Data Models:
```python
@dataclass
class PrecheckStatus:
    dns: str = "pending"       # pass, fail, pending
    udp_quic: str = "pending"  # pass, fail, pending
    tcp_h2: str = "pending"    # pass, fail, pending
    cf_api: str = "pending"    # pass, fail, pending
    suggested_protocol: str = "quic"
    hard_fail: bool = False

@dataclass
class EdgeConnection:
    conn_index: int
    ip: str = "Connecting..."
    location: str = "---"
    protocol: str = "quic"
    status: str = "INITIALIZING" # ACTIVE, DEGRADED, DISCONNECTED
    last_updated: float = 0.0

@dataclass
class ParsedLogEvent:
    timestamp: str
    stage: str      # PRECHECK, CRYPTO, EDGE_REG, TRAFFIC, HEALER, ERROR
    level: str      # INF, WRN, ERR
    message: str
    raw: str
    details: dict
```

---

### 4.2 Autonomous Healing Engine (`healing_engine.py`)

#### Playbook Matrix:
| Trigger / Signature | Root Cause | Autonomous Action | Recovery Verification |
| :--- | :--- | :--- | :--- |
| **UDP / QUIC Failure**<br>`precheck UDP Connectivity status=fail` or repeated QUIC handshake timeouts | Firewall or ISP dropping UDP port 7844 | Inject `--protocol http2` flag into cloudflared arguments and execute graceful restart. | Verify TCP HTTP/2 connection registers 4 active connections. |
| **Stale / Flapping Edge Connection**<br>Single `connIndex` dropped for > 20s while others remain active | Edge PoP routing withdrawal or transient packet drop | Trigger soft connection refresh. If unrecovered after 30s, trigger localized reconnection. | Verify dropped `connIndex` transitions back to `ACTIVE`. |
| **Complete Mesh Loss**<br>All 4 connections lost simultaneously | Upstream network interruption | Initiate exponential backoff restart sequence (2s, 6s, 18s). | Confirm precheck passes and at least 2 connections register. |
| **Origin Connection Refused**<br>`connect: connection refused` to local port | Origin service crashed or offline | Isolate fault: Tunnel is healthy, origin is down. Display origin alert HUD and trigger optional origin ping. | Origin socket responds to HTTP/TCP health probe. |
| **Authentication Failure (401/403)**<br>`Unauthorized` or invalid token | Token expired, deleted, or revoked | **Trip Circuit Breaker**: Halt all restart loops to avoid Cloudflare API rate-limiting; alert admin for re-authentication. | Requires user intervention. |

#### Circuit Breaker Safeguards:
- **Rate Limit**: Maximum 3 automated remediation restarts within any 5-minute sliding window.
- **Cool-Down Period**: Minimum 30 seconds between consecutive remediation actions.
- **Manual Control**: Operators can toggle Auto-Healing (`[H]` key) or trigger an immediate Force-Heal (`[F]` key).

---

### 4.3 TUI Visual Layout & User Experience (`tui.py`)

#### Split-Deck Workspace (Right-Hand Panel):

```
┌────────────────────────────────────────────────────────────────────────┐
│ 🛡️ CLOUDFLARE EDGE OBSERVABILITY & LOGS [AUTO-HEAL: ARMED 🟢]          │
├────────────────────────────────────────────────────────────────────────┤
│ 📡 STAGE 1: PRE-FLIGHT READINESS                                       │
│  DNS: [● PASS]   UDP(QUIC): [● PASS]   TCP(H2): [● PASS]   API: [● PASS]│
│  Selected Protocol: [QUIC (Fastest)]          Hard Fail: [FALSE]       │
├────────────────────────────────────────────────────────────────────────┤
│ ☁️ STAGE 2: ACTIVE 4-EDGE CONNECTION MATRIX                            │
│  #0 │ 2606:4700:a0::2 │ bom09 (Mumbai)    │ QUIC │ ACTIVE 🟢            │
│  #1 │ 2606:4700:a0::5 │ bom09 (Mumbai)    │ QUIC │ ACTIVE 🟢            │
│  #2 │ 2606:4700:a0::7 │ sin02 (Singapore) │ QUIC │ ACTIVE 🟢            │
│  #3 │ 2606:4700:a0::8 │ sin02 (Singapore) │ QUIC │ ACTIVE 🟢            │
├────────────────────────────────────────────────────────────────────────┤
│ 📜 LIVE STAGE STREAM  [TAB: SHOW RAW] [● AUTO-SCROLL: ON]              │
│  10:37:14 ❯ [PRECHECK] DNS Resolved successfully (region1)             │
│  10:37:14 ❯ [PRECHECK] QUIC UDP handshake verified (region1)          │
│  10:37:14 ❯ [CRYPTO]   Curve: X25519MLKEM768 (Post-Quantum Hybrid)     │
│  10:37:15 ❯ [EDGE-REG] Conn #1 registered @ bom09 [2606:4700:a0::5]    │
│  10:37:15 ❯ [EDGE-REG] Conn #3 registered @ sin02 [2606:4700:a0::7]    │
│  10:38:00 ❯ [HEALER]   Mesh health nominal (4/4 active connections)    │
└────────────────────────────────────────────────────────────────────────┘
```

#### Interactive Controls:
- **`[Tab]` or `[V]`**: Toggle between Curated Stage Log View and Raw Daemon Logs (`tunnel.log`).
- **`[H]`**: Toggle Auto-Healing Mode (`ARMED` ➔ `PAUSED`).
- **`[F]`**: Force Immediate Self-Heal Cycle.
- **`[C]`**: Clear displayed log view (retains disk logs).
- **`[Space]`**: Toggle log auto-scroll pause/resume.

---

### 4.4 Data Storage & Retention Policy

1. **Raw Log File (`~/.tunnelflare/tunnel.log`)**:
   - Contains 100% of raw unedited stdout/stderr lines from `cloudflared`.
   - File appended in stream mode; automatically rotated if size exceeds 25 MB (max 2 backup archives).
2. **Structured Event Stream (`~/.tunnelflare/events.jsonl`)**:
   - Contains serialized JSON lines for each classified stage event:
     ```json
     {"timestamp": "2026-09-28T10:37:15Z", "stage": "EDGE_REG", "level": "INF", "conn_index": 1, "ip": "2606:4700:a0::5", "location": "bom09", "protocol": "quic", "status": "ACTIVE"}
     ```
   - Retained up to 10,000 entries.

---

## 5. Non-Functional Requirements

- **Performance**: Log parsing and UI updates must execute within < 15ms per line and never block the Textual event loop.
- **Resilience**: A malformed or unrecognized log line from future `cloudflared` releases must never crash the parser; unknown lines will be gracefully categorized under `[RAW/GENERAL]` stage.
- **Terminal Compatibility**: UI layout must gracefully auto-scale across terminal widths from 80 columns (compact mode) up to 240+ columns (ultra-wide mode).
- **Zero Process Drift**: Any automated restart action executed by the healing engine must correctly update `tunnel.pid` and preserve file permissions (`0600`).
