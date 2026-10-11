import inspect
from unittest.mock import patch
import utils


def test_utils_type_annotations():
    """Ensure all function annotations evaluate properly across all Python versions."""
    for name, obj in inspect.getmembers(utils, inspect.isfunction):
        annotations = inspect.get_annotations(obj)
        assert isinstance(annotations, dict)


def test_find_competing_tunnel_daemons_parsing():
    """Verify parsing ps output filters current pid and extracts correct cloudflared run pids."""
    fake_ps = (
        "  PID COMMAND\n"
        "    1 /sbin/init\n"
        " 1234 cloudflared tunnel --config /tmp/config.yml run test-uuid-1\n"
        " 5678 cloudflared tunnel --config /tmp/config.yml run other-uuid-2\n"
        " 9999 /usr/bin/python3 main.py\n"
    )
    with patch("subprocess.check_output", return_value=fake_ps), patch("os.getpid", return_value=9999):
        # Specific tunnel
        pids = utils.find_competing_tunnel_daemons("test-uuid-1")
        assert pids == [1234]

        # All tunnels
        pids_all = utils.find_competing_tunnel_daemons(None)
        assert pids_all == [1234, 5678]


def test_terminate_stray_tunnel_daemons():
    """Verify terminate_stray_tunnel_daemons calls os.kill with SIGTERM."""
    with patch("utils.find_competing_tunnel_daemons", return_value=[1234, 5678]), \
         patch("os.kill") as mock_kill:
        count = utils.terminate_stray_tunnel_daemons("test-uuid-1")
        assert count == 2
        assert mock_kill.call_count == 2
