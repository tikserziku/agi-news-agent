#!/usr/bin/env python3
"""
Notifier - система уведомлений о находках агента
Поддержка: Telegram, Webhook, File
"""
import sqlite3
import json
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "knowledge" / "news.db"
CONFIG_PATH = Path(__file__).parent / "notifier_config.json"
ssl._create_default_https_context = ssl._create_unverified_context

# Default config
DEFAULT_CONFIG = {
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": ""
    },
    "webhook": {
        "enabled": False,
        "url": ""
    },
    "file": {
        "enabled": True,
        "path": "/home/ubuntu/agi-news-agent/notifications.json"
    },
    "thresholds": {
        "min_stars": 1000,
        "min_stars_per_day": 5,
        "min_relevance": 50
    }
}

def load_config():
    """Load notifier config"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    """Save notifier config"""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def send_telegram(message, config):
    """Send Telegram notification"""
    if not config["telegram"]["enabled"]:
        return False
    
    token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data, 
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def send_webhook(payload, config):
    """Send webhook notification"""
    if not config["webhook"]["enabled"]:
        return False
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(config["webhook"]["url"], data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return False

def save_to_file(notifications, config):
    """Save notifications to file"""
    if not config["file"]["enabled"]:
        return False
    
    path = Path(config["file"]["path"])
    
    # Load existing
    existing = []
    if path.exists():
        try:
            with open(path) as f:
                existing = json.load(f)
        except:
            pass
    
    # Add new
    existing.extend(notifications)
    
    # Keep last 100
    existing = existing[-100:]
    
    with open(path, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    return True

def format_telegram_message(findings):
    """Format findings for Telegram"""
    msg = "🤖 <b>AGI Agent - Новые находки!</b>\n\n"
    
    if findings.get("rising_stars"):
        msg += "🚀 <b>Восходящие звёзды:</b>\n"
        for repo in findings["rising_stars"][:5]:
            msg += f"  • <a href='{repo['url']}'>{repo['name']}</a>\n"
            msg += f"    ⭐{repo['stars']} ({repo['stars_per_day']}/day)\n"
    
    if findings.get("high_value"):
        msg += "\n💎 <b>Интересные проекты:</b>\n"
        for repo in findings["high_value"][:5]:
            msg += f"  • <a href='{repo['url']}'>{repo['name']}</a> ⭐{repo['stars']}\n"
    
    if findings.get("news"):
        msg += "\n📰 <b>Важные новости:</b>\n"
        for news in findings["news"][:3]:
            msg += f"  • {news['title'][:50]}...\n"
    
    msg += f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    return msg

def check_and_notify():
    """Check for notable findings and send notifications"""
    config = load_config()
    thresholds = config["thresholds"]
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    findings = {
        "timestamp": datetime.now().isoformat(),
        "rising_stars": [],
        "high_value": [],
        "news": []
    }
    
    # Check rising stars (not yet notified)
    c.execute('''SELECT repo_name, url, stars, stars_per_day, category
                 FROM github_watchlist 
                 WHERE is_rising_star = 1 AND status = 'watching'
                 AND stars_per_day >= ?
                 ORDER BY stars_per_day DESC LIMIT 10''', 
              (thresholds["min_stars_per_day"],))
    
    for row in c.fetchall():
        findings["rising_stars"].append({
            "name": row[0], "url": row[1], "stars": row[2],
            "stars_per_day": row[3], "category": row[4]
        })
    
    # Check high value repos
    c.execute('''SELECT repo_name, url, stars, category
                 FROM github_watchlist 
                 WHERE stars >= ? AND status = 'watching'
                 ORDER BY stars DESC LIMIT 10''',
              (thresholds["min_stars"],))
    
    for row in c.fetchall():
        findings["high_value"].append({
            "name": row[0], "url": row[1], "stars": row[2], "category": row[3]
        })
    
    # Check high relevance news
    c.execute('''SELECT title, url, relevance_score, source
                 FROM news WHERE relevance_score >= ?
                 ORDER BY crawled_at DESC LIMIT 5''',
              (thresholds["min_relevance"],))
    
    for row in c.fetchall():
        findings["news"].append({
            "title": row[0], "url": row[1], "score": row[2], "source": row[3]
        })
    
    conn.close()
    
    # Send notifications if we have findings
    has_findings = (findings["rising_stars"] or 
                    findings["high_value"] or 
                    findings["news"])
    
    if not has_findings:
        print("No notable findings to notify")
        return {"notified": False, "reason": "no_findings"}
    
    results = {"notified": True, "channels": []}
    
    # Telegram
    if config["telegram"]["enabled"]:
        msg = format_telegram_message(findings)
        if send_telegram(msg, config):
            results["channels"].append("telegram")
    
    # Webhook
    if config["webhook"]["enabled"]:
        if send_webhook(findings, config):
            results["channels"].append("webhook")
    
    # File (always)
    if save_to_file([findings], config):
        results["channels"].append("file")
    
    results["findings_count"] = {
        "rising_stars": len(findings["rising_stars"]),
        "high_value": len(findings["high_value"]),
        "news": len(findings["news"])
    }
    
    return results

def setup_telegram(bot_token, chat_id):
    """Setup Telegram notifications"""
    config = load_config()
    config["telegram"]["enabled"] = True
    config["telegram"]["bot_token"] = bot_token
    config["telegram"]["chat_id"] = chat_id
    save_config(config)
    
    # Test
    test_msg = "🤖 AGI News Agent подключен! Буду присылать интересные находки."
    return send_telegram(test_msg, config)

def get_pending_notifications():
    """Get notifications from file for web display"""
    config = load_config()
    path = Path(config["file"]["path"])
    
    if not path.exists():
        return []
    
    with open(path) as f:
        return json.load(f)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    
    if cmd == "check":
        result = check_and_notify()
        print(json.dumps(result, indent=2))
    elif cmd == "setup_telegram":
        if len(sys.argv) < 4:
            print("Usage: notifier.py setup_telegram <bot_token> <chat_id>")
        else:
            ok = setup_telegram(sys.argv[2], sys.argv[3])
            print("Telegram setup:", "OK" if ok else "FAILED")
    elif cmd == "pending":
        notifications = get_pending_notifications()
        print(json.dumps(notifications, indent=2, ensure_ascii=False))
    elif cmd == "config":
        config = load_config()
        print(json.dumps(config, indent=2))

def format_channel_post(findings):
    """Format findings for public channel - more detailed"""
    msg = "🤖 <b>AI Agent News - Дайджест</b>\n"
    msg += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
    
    if findings.get("rising_stars"):
        msg += "🚀 <b>ВОСХОДЯЩИЕ ЗВЁЗДЫ</b>\n"
        msg += "<i>Молодые проекты с быстрым ростом</i>\n\n"
        for repo in findings["rising_stars"][:5]:
            msg += f"📦 <a href='{repo['url']}'>{repo['name']}</a>\n"
            msg += f"   ⭐ {repo['stars']} ({repo['stars_per_day']} stars/day)\n"
            msg += f"   📂 {repo.get('category', 'N/A')}\n\n"
    
    if findings.get("high_value"):
        msg += "💎 <b>ТОП ПРОЕКТЫ</b>\n\n"
        for repo in findings["high_value"][:3]:
            msg += f"• <a href='{repo['url']}'>{repo['name']}</a> - ⭐{repo['stars']}\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🔗 Dashboard: http://158.180.56.74/agi-agent/\n"
    msg += "🤖 Автоматический мониторинг от AGI News Agent"
    
    return msg

def send_to_channel(channel_id=None):
    """Send digest to public channel"""
    config = load_config()
    
    if not channel_id:
        channel_id = config["telegram"].get("channel_id")
    
    if not channel_id:
        return {"error": "No channel_id configured"}
    
    # Get findings
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    findings = {"rising_stars": [], "high_value": []}
    
    c.execute('''SELECT repo_name, url, stars, stars_per_day, category
                 FROM github_watchlist WHERE is_rising_star = 1
                 ORDER BY stars_per_day DESC LIMIT 5''')
    for row in c.fetchall():
        findings["rising_stars"].append({
            "name": row[0], "url": row[1], "stars": row[2],
            "stars_per_day": row[3], "category": row[4]
        })
    
    c.execute('''SELECT repo_name, url, stars FROM github_watchlist
                 ORDER BY stars DESC LIMIT 5''')
    for row in c.fetchall():
        findings["high_value"].append({"name": row[0], "url": row[1], "stars": row[2]})
    
    conn.close()
    
    if not findings["rising_stars"] and not findings["high_value"]:
        return {"error": "No findings to post"}
    
    # Send to channel
    msg = format_channel_post(findings)
    token = config["telegram"]["bot_token"]
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": channel_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode('utf-8')
    
    try:
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return {"success": True, "channel_id": channel_id}
    except Exception as e:
        return {"error": str(e)}
