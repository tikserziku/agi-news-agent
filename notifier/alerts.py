#!/usr/bin/env python3
"""Alert System - Notifications for important discoveries"""
import sqlite3
import json
import urllib.request
import ssl
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"
ALERTS_FILE = Path(__file__).parent.parent / "logs" / "alerts.json"
ssl._create_default_https_context = ssl._create_unverified_context

CONFIG = {
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "webhook_url": "",
    "min_growth_score": 100,
    "priority_keywords": ["mcp", "protocol", "agent", "claude", "api", "sdk", "ucp"]
}

def init_alerts_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY, alert_type TEXT, title TEXT, message TEXT,
        url TEXT, priority TEXT DEFAULT 'normal', sent BOOLEAN DEFAULT 0,
        sent_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def check_for_alerts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    alerts = []
    
    # Hot GitHub repos
    try:
        c.execute('''SELECT repo_name, stars, stars_per_day, growth_score, url 
                     FROM github_watchlist 
                     WHERE category IN ('hot', 'rising') OR growth_score > ?
                     ORDER BY growth_score DESC LIMIT 10''', (CONFIG['min_growth_score'],))
        for row in c.fetchall():
            alerts.append({
                "type": "github", "title": f"HOT Repo: {row[0]}",
                "message": f"Stars: {row[1]} | Growth: {row[2]}/day | Score: {row[3]}",
                "url": row[4], "priority": "high" if row[2] > 30 else "normal"
            })
    except: pass
    
    # Important blog posts  
    c.execute('''SELECT source, title, content, url FROM news 
                 WHERE source LIKE 'blog_%' AND relevance_score >= 30
                 ORDER BY id DESC LIMIT 10''')
    for row in c.fetchall():
        alerts.append({
            "type": "blog", "title": f"{row[0].replace('blog_','').upper()}: {row[1][:60]}",
            "message": (row[2] or "")[:200], "url": row[3],
            "priority": "high" if "anthropic" in row[0] else "normal"
        })
    
    conn.close()
    return alerts

def save_alerts_to_file(alerts):
    existing = []
    if ALERTS_FILE.exists():
        try:
            with open(ALERTS_FILE) as f: existing = json.load(f)
        except: pass
    
    for a in alerts: a['timestamp'] = datetime.now().isoformat()
    existing = alerts + existing
    existing = existing[:100]
    
    with open(ALERTS_FILE, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return len(alerts)

def process_alerts():
    init_alerts_table()
    alerts = check_for_alerts()
    if alerts:
        save_alerts_to_file(alerts)
        print(f"Found {len(alerts)} alerts")
        for a in alerts[:10]:
            mark = "HIGH" if a['priority'] == 'high' else "    "
            print(f"  [{mark}] {a['title']}")
    return {"alerts": len(alerts)}

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        result = process_alerts()
        print(json.dumps(result))
