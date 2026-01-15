#!/usr/bin/env python3
"""
News Analyzer - извлечение знаний из новостей
Определяет релевантность и извлекает технологии для внедрения
"""
import sqlite3
import json
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"

# Паттерны для определения важности
IMPORTANCE_PATTERNS = {
    "critical": [
        r"anthropic", r"claude", r"mcp", r"model context protocol",
        r"breaking", r"announced", r"launched", r"released"
    ],
    "high": [
        r"agent", r"agentic", r"llm", r"gpt-\d", r"gemini",
        r"protocol", r"api", r"sdk", r"framework"
    ],
    "medium": [
        r"ai", r"machine learning", r"neural", r"transformer",
        r"open.?source", r"github"
    ]
}

# Категории технологий
TECH_CATEGORIES = {
    "protocol": [r"protocol", r"standard", r"specification", r"api"],
    "framework": [r"framework", r"library", r"sdk", r"toolkit"],
    "model": [r"model", r"llm", r"gpt", r"claude", r"gemini"],
    "tool": [r"tool", r"cli", r"app", r"service"],
    "concept": [r"agent", r"agentic", r"autonomous", r"self-"]
}

def calculate_relevance(title, content):
    """Calculate relevance score 0-100"""
    text = f"{title} {content}".lower()
    score = 0
    
    # Critical keywords +30 each
    for pattern in IMPORTANCE_PATTERNS["critical"]:
        if re.search(pattern, text, re.I):
            score += 30
    
    # High keywords +15 each
    for pattern in IMPORTANCE_PATTERNS["high"]:
        if re.search(pattern, text, re.I):
            score += 15
    
    # Medium keywords +5 each
    for pattern in IMPORTANCE_PATTERNS["medium"]:
        if re.search(pattern, text, re.I):
            score += 5
    
    return min(score, 100)

def extract_technologies(title, content):
    """Extract technology mentions"""
    text = f"{title} {content}"
    technologies = []
    
    # Known tech patterns
    tech_patterns = [
        (r"MCP|Model Context Protocol", "MCP"),
        (r"UCP|Universal Commerce Protocol", "UCP"),
        (r"A2A|Agent.?to.?Agent", "A2A"),
        (r"AP2|Agent Payments Protocol", "AP2"),
        (r"Claude\s*\d*\.?\d*", "Claude"),
        (r"GPT-\d+", "GPT"),
        (r"Gemini", "Gemini"),
    ]
    
    for pattern, name in tech_patterns:
        if re.search(pattern, text, re.I):
            technologies.append(name)
    
    return list(set(technologies))

def determine_category(text):
    """Determine technology category"""
    text = text.lower()
    for category, patterns in TECH_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return category
    return "general"

def analyze_news():
    """Analyze all unanalyzed news"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get unanalyzed news
    c.execute("SELECT id, source, title, content, url FROM news WHERE analyzed = 0")
    news_items = c.fetchall()
    
    analyzed_count = 0
    knowledge_count = 0
    tech_count = 0
    
    for news_id, source, title, content, url in news_items:
        # Calculate relevance
        relevance = calculate_relevance(title, content or "")
        
        # Update news with relevance
        c.execute("UPDATE news SET analyzed = 1, relevance_score = ? WHERE id = ?",
                  (relevance, news_id))
        analyzed_count += 1
        
        # Extract technologies if relevant
        if relevance >= 30:
            technologies = extract_technologies(title, content or "")
            
            for tech in technologies:
                # Save to knowledge
                c.execute('''INSERT OR IGNORE INTO knowledge 
                            (news_id, category, key, value, importance)
                            VALUES (?, ?, ?, ?, ?)''',
                         (news_id, "technology", tech, f"Found in: {title[:100]}", 
                          "high" if relevance >= 60 else "medium"))
                knowledge_count += 1
                
                # Add to technologies table
                c.execute('''INSERT OR IGNORE INTO technologies 
                            (name, description, source_news_id, status)
                            VALUES (?, ?, ?, 'discovered')''',
                         (tech, f"Discovered from {source}: {title[:200]}", news_id))
                if c.rowcount > 0:
                    tech_count += 1
    
    conn.commit()
    conn.close()
    
    return {
        "analyzed": analyzed_count,
        "knowledge_extracted": knowledge_count,
        "new_technologies": tech_count
    }

def get_high_relevance_news(min_score=50):
    """Get highly relevant news"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, source, title, relevance_score, url 
                 FROM news WHERE relevance_score >= ? 
                 ORDER BY relevance_score DESC''', (min_score,))
    results = c.fetchall()
    conn.close()
    return results

def get_discovered_technologies():
    """Get all discovered technologies"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT name, description, status FROM technologies 
                 ORDER BY id DESC''')
    results = c.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    
    if cmd == "analyze":
        result = analyze_news()
        print(json.dumps(result, indent=2))
    elif cmd == "relevant":
        news = get_high_relevance_news(30)
        for n in news:
            print(f"[{n[3]}] {n[1]}: {n[2][:60]}...")
    elif cmd == "technologies":
        techs = get_discovered_technologies()
        for t in techs:
            print(f"[{t[2]}] {t[0]}: {t[1][:60]}...")
