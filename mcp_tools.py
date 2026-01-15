#!/usr/bin/env python3
"""
MCP Tools для AGI News Agent
Позволяет управлять агентом через MCP-HUB
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "knowledge" / "news.db"

def tool_agent_status():
    """Get AGI Agent status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    status = {"agent": "AGI News Agent", "status": "active"}
    
    for table in ["news", "knowledge", "technologies", "agent_actions"]:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        status[table] = c.fetchone()[0]
    
    c.execute("SELECT action_type, executed_at FROM agent_actions ORDER BY id DESC LIMIT 1")
    last = c.fetchone()
    if last:
        status["last_run"] = {"action": last[0], "at": last[1]}
    
    conn.close()
    return status

def tool_agent_news(limit=5, min_score=30):
    """Get relevant news from agent"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT source, title, relevance_score, url FROM news 
                 WHERE relevance_score >= ? ORDER BY relevance_score DESC LIMIT ?''',
              (min_score, limit))
    results = [{"source": r[0], "title": r[1], "score": r[2], "url": r[3]} for r in c.fetchall()]
    conn.close()
    return results

def tool_agent_technologies():
    """Get discovered technologies"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT name, description, status FROM technologies ORDER BY id DESC''')
    results = [{"name": r[0], "description": r[1], "status": r[2]} for r in c.fetchall()]
    conn.close()
    return results

def tool_agent_run():
    """Trigger agent run"""
    import subprocess
    result = subprocess.run(
        ["python3", "/home/ubuntu/agi-news-agent/main.py", "run"],
        capture_output=True, text=True, cwd="/home/ubuntu/agi-news-agent"
    )
    return {"output": result.stdout, "error": result.stderr, "code": result.returncode}

# Export for MCP-HUB integration
TOOLS = {
    "agent_status": tool_agent_status,
    "agent_news": tool_agent_news,
    "agent_technologies": tool_agent_technologies,
    "agent_run": tool_agent_run
}

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd in TOOLS:
        result = TOOLS[cmd]()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Available tools: {list(TOOLS.keys())}")
