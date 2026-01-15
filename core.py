#!/usr/bin/env python3
"""
AGI News Agent - Self-Learning System
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "knowledge" / "news.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY,
        source TEXT, title TEXT, content TEXT, url TEXT UNIQUE,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        analyzed BOOLEAN DEFAULT 0, relevance_score REAL DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY, news_id INTEGER,
        category TEXT, key TEXT, value TEXT,
        importance TEXT DEFAULT 'medium',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS technologies (
        id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT,
        source_news_id INTEGER, status TEXT DEFAULT 'discovered',
        architecture TEXT, implementation_plan TEXT, deployed_at TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS agent_actions (
        id INTEGER PRIMARY KEY, action_type TEXT, description TEXT,
        input_data TEXT, output_data TEXT, success BOOLEAN,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print("Database initialized")

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    stats = {}
    for table in ['news', 'knowledge', 'technologies', 'agent_actions']:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        stats[table] = c.fetchone()[0]
    conn.close()
    return stats

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "init": init_db()
    elif cmd == "stats": print(json.dumps(get_stats(), indent=2))
