#!/bin/bash
echo "=== Cloudflared Processes ==="
sudo ps -ef | grep [c]loudflared

echo -e "\n=== Tunnel PID File ==="
if [ -f ~/.tunnelflare/tunnel.pid ]; then
    cat ~/.tunnelflare/tunnel.pid
    echo " (PID exists)"
    PID=$(cat ~/.tunnelflare/tunnel.pid)
    if ps -p $PID > /dev/null; then
        echo "Process $PID is RUNNING."
    else
        echo "Process $PID is NOT running."
    fi
else
    echo "tunnel.pid NOT found."
fi

echo -e "\n=== Tunnel Log File (Last 10 lines) ==="
if [ -f ~/.tunnelflare/tunnel.log ]; then
    ls -l ~/.tunnelflare/tunnel.log
    tail -n 10 ~/.tunnelflare/tunnel.log
else
    echo "tunnel.log NOT found."
fi

echo -e "\n=== Directory Permissions ==="
ls -ld ~/.tunnelflare
ls -ld ~/.cloudflared
