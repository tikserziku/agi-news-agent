#!/bin/bash
URL_FILE="/home/ubuntu/agi-news-agent/current_tunnel_url.txt"
OLD_URL=$(cat "$URL_FILE" 2>/dev/null)

# Get new URL
NEW_URL=$(timeout 20 /usr/local/bin/cloudflared tunnel --url http://127.0.0.1:3457 2>&1 | grep -oP "https://[a-z0-9-]+\.trycloudflare\.com" | head -1)

if [ -n "$NEW_URL" ] && [ "$NEW_URL" != "$OLD_URL" ]; then
    echo "$NEW_URL" > "$URL_FILE"
    # Send to Telegram
    BOT_TOKEN="7579834718:AAHOxEjB6GvqKFA0ztql2qKvOg0u3LqDU2M"
    CHAT_ID="171656163"
    MSG="🔗 AGI Agent Dashboard URL обновлён:%0A$NEW_URL"
    curl -s "https://api.telegram.org/bot$BOT_TOKEN/sendMessage?chat_id=$CHAT_ID&text=$MSG" > /dev/null
fi
