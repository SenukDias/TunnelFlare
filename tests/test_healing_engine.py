"""
Unit tests for TunnelFlare autonomous healing engine, FSM states, and playbooks.
"""

from pathlib import Path
import pytest
from healing_engine import HealingEngine, HealthFSMState
from log_parser import LogParser


def test_fsm_initial_and_precheck_states(tmp_path: Path):
    parser = LogParser(jsonl_path=tmp_path / "events.jsonl")
    engine = HealingEngine(parser=parser)

    # Stopped state
    state = engine.evaluate_health(tunnel_running=False)
    assert state == HealthFSMState.STOPPED

    # Prechecking state
    state = engine.evaluate_health(tunnel_running=True)
    assert state == HealthFSMState.PRECHECKING


def test_protocol_fallback_on_quic_fail(tmp_path: Path):
    parser = LogParser(jsonl_path=tmp_path / "events.jsonl")
    restart_calls = []

    def mock_restart(opts: dict) -> bool:
        restart_calls.append(opts)
        return True

    engine = HealingEngine(parser=parser, restart_callback=mock_restart)

    # Simulate UDP/QUIC precheck failure
    event = parser.parse_line(
        '2026-09-28T10:37:14Z INF precheck component="UDP Connectivity" details="QUIC failed: timeout" status=fail target=region1.v2.argotunnel.com'
    )
    assert event is not None

    record = engine.process_event(event, tunnel_running=True)
    assert record is not None
    assert record.action_taken == "PROTOCOL_FALLBACK_HTTP2"
    assert record.status == "SUCCESS"
    assert engine.active_protocol == "http2"
    assert len(restart_calls) == 1
    assert restart_calls[0]["protocol"] == "http2"


def test_circuit_breaker_on_auth_failure(tmp_path: Path):
    parser = LogParser(jsonl_path=tmp_path / "events.jsonl")
    engine = HealingEngine(parser=parser)

    event = parser.parse_line(
        '2026-09-28T10:37:14Z ERR Failed to authenticate tunnel: Unauthorized access'
    )
    assert event is not None

    record = engine.process_event(event, tunnel_running=True)
    assert record is not None
    assert record.action_taken == "TRIP_CIRCUIT_BREAKER"
    assert engine.circuit_tripped is True
    assert engine.state == HealthFSMState.CIRCUIT_TRIPPED

    # Reset circuit breaker
    engine.reset_circuit_breaker()
    assert engine.circuit_tripped is False


def test_rate_limiting_circuit_breaker(tmp_path: Path):
    parser = LogParser(jsonl_path=tmp_path / "events.jsonl")
    engine = HealingEngine(parser=parser, restart_callback=lambda opts: True)
    engine.COOLDOWN_SECONDS = 0  # Disable cooldown to test window capacity

    # Execute 3 actions
    for _ in range(3):
        engine._execute_mesh_reconnect("TEST")

    # 4th action should be rejected by circuit breaker
    assert engine._can_execute_action() is False
    assert engine.circuit_tripped is True
    assert "Rate limit exceeded" in engine.trip_reason
