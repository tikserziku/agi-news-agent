#!/usr/bin/env python3
"""
News Crawler - сбор новостей из разных источников
Источники: Anthropic, Google AI, HackerNews, GitHub, ArXiv
"""
import sqlite3
import json
import re
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"

# Отключаем SSL верификацию для простоты
ssl._create_default_https_context = ssl._create_unverified_context

SOURCES = {
    "hackernews": {
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "type": "api",
        "keywords": ["ai", "llm", "anthropic", "claude", "mcp", "agent", "google", "openai", "gpt"]
    },
    "github_trending": {
        "url": "https://api.github.com/search/repositories?q=mcp+OR+llm+OR+agent&sort=updated&order=desc",
        "type": "github"
    }
}

def fetch_url(url, headers=None):
    """Fetch URL content"""
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "AGI-News-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def crawl_hackernews():
    """Crawl HackerNews for AI-related stories"""
    news = []
    keywords = SOURCES["hackernews"]["keywords"]
    
    # Get top stories
    data = fetch_url(SOURCES["hackernews"]["url"])
    if not data:
        return news
    
    story_ids = json.loads(data)[:50]  # Top 50
    
    for sid in story_ids[:20]:  # Check first 20
        story_data = fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if not story_data:
            continue
        
        story = json.loads(story_data)
        title = story.get("title", "").lower()
        
        # Check keywords
        if any(kw in title for kw in keywords):
            news.append({
                "source": "hackernews",
                "title": story.get("title"),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                "content": f"HN Score: {story.get('score', 0)}, Comments: {story.get('descendants', 0)}"
            })
    
    return news

def crawl_github():
    """Crawl GitHub for MCP/AI related repos"""
    news = []
    headers = {"User-Agent": "AGI-News-Agent/1.0", "Accept": "application/vnd.github.v3+json"}
    
    data = fetch_url(SOURCES["github_trending"]["url"], headers)
    if not data:
        return news
    
    repos = json.loads(data).get("items", [])[:10]
    
    for repo in repos:
        news.append({
            "source": "github",
            "title": f"{repo['full_name']}: {(repo.get('description') or 'No description')[:100]}",
            "url": repo["html_url"],
            "content": f"Stars: {repo['stargazers_count']}, Language: {repo.get('language', 'Unknown')}"
        })
    
    return news

def save_news(news_list):
    """Save news to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved = 0
    for news in news_list:
        try:
            c.execute('''INSERT OR IGNORE INTO news (source, title, content, url)
                         VALUES (?, ?, ?, ?)''',
                      (news["source"], news["title"], news["content"], news["url"]))
            if c.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"Error saving: {e}")
    
    conn.commit()
    conn.close()
    return saved

def crawl_all():
    """Run all crawlers"""
    all_news = []
    
    print("Crawling HackerNews...")
    all_news.extend(crawl_hackernews())
    
    print("Crawling GitHub...")
    all_news.extend(crawl_github())
    
    print(f"Found {len(all_news)} items")
    saved = save_news(all_news)
    print(f"Saved {saved} new items")
    
    return {"found": len(all_news), "saved": saved}

if __name__ == "__main__":
    result = crawl_all()
    print(json.dumps(result))
