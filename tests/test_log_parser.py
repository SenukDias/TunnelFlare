"""
Unit tests for TunnelFlare structured log parser, stage classifier, and PoP resolver.
"""

import json
from pathlib import Path
import pytest
from log_parser import LogParser, resolve_pop_name


def test_pop_name_resolution():
    assert "Mumbai" in resolve_pop_name("bom09")
    assert "Singapore" in resolve_pop_name("sin02")
    assert "Frankfurt" in resolve_pop_name("fra15")
    assert resolve_pop_name("unknown99") == "UNKNOWN99"
    assert resolve_pop_name("---") == "Unknown"


def test_precheck_parsing(tmp_path: Path):
    jsonl_file = tmp_path / "test_events.jsonl"
    parser = LogParser(jsonl_path=jsonl_file)

    # 1. DNS Precheck
    line_dns = '2026-09-28T10:37:14Z INF precheck component="DNS Resolution" details="DNS Resolved successfully" run_id=7c233629 status=pass target=region1.v2.argotunnel.com'
    ev1 = parser.parse_line(line_dns)
    assert ev1 is not None
    assert ev1.stage == "PRECHECK"
    assert parser.precheck.dns == "pass"

    # 2. UDP Connectivity Precheck
    line_udp = '2026-09-28T10:37:14Z INF precheck component="UDP Connectivity" details="QUIC connection successful" run_id=7c233629 status=pass target=region1.v2.argotunnel.com'
    ev2 = parser.parse_line(line_udp)
    assert ev2 is not None
    assert parser.precheck.udp_quic == "pass"

    # 3. TCP Connectivity Precheck
    line_tcp = '2026-09-28T10:37:14Z INF precheck component="TCP Connectivity" details="HTTP/2 connection successful" run_id=7c233629 status=pass target=region1.v2.argotunnel.com'
    parser.parse_line(line_tcp)
    assert parser.precheck.tcp_h2 == "pass"

    # 4. Cloudflare API Reachability Precheck
    line_api = '2026-09-28T10:37:14Z INF precheck component="Cloudflare API" details="API is reachable" run_id=7c233629 status=pass target=api.cloudflare.com:443'
    parser.parse_line(line_api)
    assert parser.precheck.cf_api == "pass"

    # 5. Precheck summary
    line_sum = '2026-09-28T10:37:14Z INF precheck complete hard_fail=false run_id=7c233629 suggested_protocol=quic'
    parser.parse_line(line_sum)
    assert parser.precheck.suggested_protocol == "quic"
    assert parser.precheck.hard_fail is False
    assert parser.precheck.is_all_passed() is True


def test_curve_and_edge_registration(tmp_path: Path):
    jsonl_file = tmp_path / "test_events.jsonl"
    parser = LogParser(jsonl_path=jsonl_file)

    # 1. Curve preference
    line_curve = '2026-09-28T10:37:14Z INF Tunnel connection curve preferences: [X25519MLKEM768 CurveID(65074) CurveP256] connIndex=2 event=0 ip=2606:4700:a0::2'
    ev_curve = parser.parse_line(line_curve)
    assert ev_curve is not None
    assert ev_curve.stage == "CRYPTO"
    assert "X25519MLKEM768" in parser.connections[2].curve
    assert parser.connections[2].ip == "2606:4700:a0::2"

    # 2. Registered tunnel connection
    line_reg = '2026-09-28T10:37:15Z INF Registered tunnel connection connIndex=1 connection=9b711612-1e44-490c-b382-e51247e758b6 event=0 ip=2606:4700:a0::5 location=bom09 protocol=quic'
    ev_reg = parser.parse_line(line_reg)
    assert ev_reg is not None
    assert ev_reg.stage == "EDGE_REG"
    assert parser.connections[1].status == "ACTIVE"
    assert parser.connections[1].ip == "2606:4700:a0::5"
    assert parser.connections[1].location == "bom09"
    assert parser.connections[1].protocol == "quic"
    assert parser.get_active_count() == 1

    # 3. Disconnection
    line_unreg = '2026-09-28T10:38:00Z INF Unregistered tunnel connection connIndex=1 connection=9b711612'
    parser.parse_line(line_unreg)
    assert parser.connections[1].status == "DISCONNECTED"
    assert parser.get_active_count() == 0


def test_jsonl_persistence(tmp_path: Path):
    jsonl_file = tmp_path / "test_events.jsonl"
    parser = LogParser(jsonl_path=jsonl_file)

    parser.parse_line('2026-09-28T10:37:14Z INF precheck component="DNS Resolution" details="DNS Resolved successfully" status=pass target=region1.v2.argotunnel.com')
    parser.parse_line('2026-09-28T10:37:15Z INF Registered tunnel connection connIndex=0 ip=2606:4700:a0::1 location=sin02 protocol=quic')

    assert jsonl_file.exists()
    lines = jsonl_file.read_text().strip().splitlines()
    assert len(lines) == 2

    data1 = json.loads(lines[0])
    assert data1["stage"] == "PRECHECK"

    data2 = json.loads(lines[1])
    assert data2["stage"] == "EDGE_REG"
    assert data2["ip"] == "2606:4700:a0::1"
    assert data2["location"] == "sin02"
