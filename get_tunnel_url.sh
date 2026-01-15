#!/bin/bash
# Get current tunnel URL
LOG=$(sudo journalctl -u agi-tunnel --since "5 minutes ago" 2>/dev/null | grep -oP "https://[a-z0-9-]+\.trycloudflare\.com" | tail -1)
if [ -z "$LOG" ]; then
    # Try from process
    timeout 15 /usr/local/bin/cloudflared tunnel --url http://127.0.0.1:3457 2>&1 | grep -oP "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
else
    echo "$LOG"
fi
