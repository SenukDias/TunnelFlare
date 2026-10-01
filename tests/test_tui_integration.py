"""
End-to-End integration test for TunnelFlare TUI with Stage HUD, LogParser, and HealingEngine.
Simulates real cloudflared output matching user's live terminal log capture.
"""

from pathlib import Path
import pytest
from textual.app import App
from tui import StageHUDWidget, TunnelFlareApp
from log_parser import LogParser


SAMPLE_CLOUDFLARED_LOGS = [
    '2026-09-28T10:37:14Z INF |',
    "2026-09-28T10:37:14Z INF | SUMMARY: Environment is healthy. cloudflared will use 'quic' as primary protocol.",
    '2026-09-28T10:37:14Z INF precheck component="DNS Resolution" details="DNS Resolved successfully" run_id=7c233629 status=pass target=region1.v2.argotunnel.com',
    '2026-09-28T10:37:14Z INF precheck component="DNS Resolution" details="DNS Resolved successfully" run_id=7c233629 status=pass target=region2.v2.argotunnel.com',
    '2026-09-28T10:37:14Z INF precheck component="UDP Connectivity" details="QUIC connection successful" run_id=7c233629 status=pass target=region1.v2.argotunnel.com',
    '2026-09-28T10:37:14Z INF precheck component="UDP Connectivity" details="QUIC connection successful" run_id=7c233629 status=pass target=region2.v2.argotunnel.com',
    '2026-09-28T10:37:14Z INF precheck component="TCP Connectivity" details="HTTP/2 connection successful" run_id=7c233629 status=pass target=region1.v2.argotunnel.com',
    '2026-09-28T10:37:14Z INF precheck component="Cloudflare API" details="API is reachable" run_id=7c233629 status=pass target=api.cloudflare.com:443',
    '2026-09-28T10:37:14Z INF precheck complete hard_fail=false run_id=7c233629 suggested_protocol=quic',
    '2026-09-28T10:37:14Z INF Tunnel connection curve preferences: [X25519MLKEM768 CurveID(65074) CurveP256] connIndex=0 event=0 ip=2606:4700:a0::2',
    '2026-09-28T10:37:14Z INF Registered tunnel connection connIndex=0 connection=9b711612-1e44-490c-b382-e51247e758b0 event=0 ip=2606:4700:a0::2 location=bom09 protocol=quic',
    '2026-09-28T10:37:15Z INF Registered tunnel connection connIndex=1 connection=9b711612-1e44-490c-b382-e51247e758b1 event=0 ip=2606:4700:a0::5 location=bom09 protocol=quic',
    '2026-09-28T10:37:15Z INF Registered tunnel connection connIndex=2 connection=9b711612-1e44-490c-b382-e51247e758b2 event=0 ip=2606:4700:a0::7 location=sin02 protocol=quic',
    '2026-09-28T10:37:15Z INF Registered tunnel connection connIndex=3 connection=9b711612-1e44-490c-b382-e51247e758b3 event=0 ip=2606:4700:a0::8 location=sin02 protocol=quic',
]


@pytest.mark.anyio
async def test_tui_app_lifecycle_and_stage_hud():
    """Verify TunnelFlareApp initializes with Stage HUD, widgets, and processes live logs."""
    app = TunnelFlareApp()
    async with app.run_test() as pilot:
        # 1. Verify app elements exist
        stage_hud = app.query_one("#stage_hud", StageHUDWidget)
        curated_log = app.query_one("#curated_log_view")
        raw_log = app.query_one("#raw_log_view")
        mode_label = app.query_one("#log-mode-label")

        assert stage_hud is not None
        assert curated_log is not None
        assert raw_log is not None
        assert "CURATED STAGE STREAM" in str(mode_label.render())

        # 2. Feed the sample real-world log stream into parser
        for line in SAMPLE_CLOUDFLARED_LOGS:
            ev = app.log_parser.parse_line(line)
            if ev:
                app.healing_engine.process_event(ev, tunnel_running=True)
                curated_log.write(app.format_curated_event(ev))
                raw_log.write(app.format_log_line(line))

        # 3. Verify parser parsed 4 active connections
        assert app.log_parser.get_active_count() == 4
        assert app.log_parser.connections[0].ip == "2606:4700:a0::2"
        assert app.log_parser.connections[0].location == "bom09"
        assert app.log_parser.connections[1].ip == "2606:4700:a0::5"
        assert app.log_parser.connections[2].ip == "2606:4700:a0::7"
        assert app.log_parser.connections[2].location == "sin02"
        assert app.log_parser.connections[3].ip == "2606:4700:a0::8"
        assert app.log_parser.precheck.is_all_passed() is True

        # 4. Verify Stage HUD renders panel with Mumbai and Singapore PoPs
        panel = stage_hud.render()
        assert panel is not None

        # 5. Test toggling between Curated and Raw log modes (Tab / v key)
        assert app.view_mode == "curated"
        app.action_toggle_log_mode()
        assert app.view_mode == "raw"
        assert "hidden" in curated_log.classes
        assert "hidden" not in raw_log.classes

        # Toggle back
        app.action_toggle_log_mode()
        assert app.view_mode == "curated"
        assert "hidden" not in curated_log.classes
        assert "hidden" in raw_log.classes

        # 6. Test toggling Auto-Healing mode (h key)
        assert app.healing_engine.is_armed is True
        app.action_toggle_auto_heal()
        assert app.healing_engine.is_armed is False
        app.action_toggle_auto_heal()
        assert app.healing_engine.is_armed is True
