#!/usr/bin/env python3
"""
Blog Crawlers - Anthropic, Google AI, OpenAI blogs
Используем RSS/Atom feeds и web scraping
"""
import sqlite3
import json
import urllib.request
import ssl
import re
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"
ssl._create_default_https_context = ssl._create_unverified_context

HEADERS = {"User-Agent": "AGI-News-Agent/1.0"}

# Blog sources
SOURCES = {
    "anthropic": {
        "rss": "https://www.anthropic.com/rss.xml",
        "web": "https://www.anthropic.com/news",
        "keywords": ["claude", "mcp", "model", "safety", "agent", "api"]
    },
    "google_ai": {
        "rss": "https://blog.google/technology/ai/rss/",
        "keywords": ["gemini", "ai", "agent", "model", "llm", "protocol"]
    },
    "openai": {
        "rss": "https://openai.com/blog/rss.xml",
        "keywords": ["gpt", "api", "agent", "model", "assistant"]
    }
}

class SimpleHTMLParser(HTMLParser):
    """Extract text from HTML"""
    def __init__(self):
        super().__init__()
        self.text = []
        
    def handle_data(self, data):
        self.text.append(data.strip())
    
    def get_text(self):
        return ' '.join(filter(None, self.text))

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_rss(xml_content, source_name):
    """Simple RSS/Atom parser"""
    items = []
    
    # Find all items/entries
    item_pattern = r'<(?:item|entry)>(.*?)</(?:item|entry)>'
    matches = re.findall(item_pattern, xml_content, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        item = {}
        
        # Title
        title_match = re.search(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', match, re.DOTALL)
        if title_match:
            item['title'] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        # Link
        link_match = re.search(r'<link[^>]*>([^<]+)</link>', match) or \
                     re.search(r'<link[^>]*href="([^"]+)"', match)
        if link_match:
            item['url'] = link_match.group(1).strip()
        
        # Description/Summary
        desc_match = re.search(r'<(?:description|summary)[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</(?:description|summary)>', 
                               match, re.DOTALL)
        if desc_match:
            parser = SimpleHTMLParser()
            parser.feed(desc_match.group(1))
            item['description'] = parser.get_text()[:500]
        
        # Date
        date_match = re.search(r'<(?:pubDate|published|updated)[^>]*>([^<]+)</(?:pubDate|published|updated)>', match)
        if date_match:
            item['date'] = date_match.group(1).strip()
        
        if item.get('title') and item.get('url'):
            item['source'] = source_name
            items.append(item)
    
    return items

def crawl_anthropic():
    """Crawl Anthropic news"""
    items = []
    
    # Try RSS
    rss_content = fetch_url(SOURCES["anthropic"]["rss"])
    if rss_content:
        items = parse_rss(rss_content, "anthropic")
        print(f"  Anthropic RSS: {len(items)} items")
    
    # Try web scraping as backup
    if not items:
        web_content = fetch_url(SOURCES["anthropic"]["web"])
        if web_content:
            # Find article links
            links = re.findall(r'href="(/news/[^"]+)"', web_content)
            for link in list(set(links))[:10]:
                url = f"https://www.anthropic.com{link}"
                # Extract title from link
                title = link.split('/')[-1].replace('-', ' ').title()
                items.append({
                    "source": "anthropic",
                    "title": title,
                    "url": url,
                    "description": "Anthropic News"
                })
            print(f"  Anthropic Web: {len(items)} items")
    
    return items

def crawl_google_ai():
    """Crawl Google AI blog"""
    items = []
    
    rss_content = fetch_url(SOURCES["google_ai"]["rss"])
    if rss_content:
        all_items = parse_rss(rss_content, "google_ai")
        # Filter AI-related
        keywords = SOURCES["google_ai"]["keywords"]
        for item in all_items:
            text = f"{item.get('title', '')} {item.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                items.append(item)
        print(f"  Google AI: {len(items)} AI-related items (from {len(all_items)} total)")
    
    return items

def crawl_openai():
    """Crawl OpenAI blog"""
    items = []
    
    rss_content = fetch_url(SOURCES["openai"]["rss"])
    if rss_content:
        items = parse_rss(rss_content, "openai")
        print(f"  OpenAI: {len(items)} items")
    
    return items

def save_blog_items(items):
    """Save blog items to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved = 0
    for item in items:
        try:
            c.execute('''INSERT OR IGNORE INTO news (source, title, content, url)
                         VALUES (?, ?, ?, ?)''',
                      (f"blog_{item['source']}", 
                       item.get('title', 'No title'),
                       item.get('description', ''),
                       item.get('url', '')))
            if c.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"Error saving: {e}")
    
    conn.commit()
    conn.close()
    return saved

def crawl_all_blogs():
    """Crawl all blog sources"""
    all_items = []
    
    print("Crawling blogs...")
    
    print("  Anthropic...")
    all_items.extend(crawl_anthropic())
    
    print("  Google AI...")
    all_items.extend(crawl_google_ai())
    
    print("  OpenAI...")
    all_items.extend(crawl_openai())
    
    saved = save_blog_items(all_items)
    
    return {"found": len(all_items), "saved": saved}

if __name__ == "__main__":
    result = crawl_all_blogs()
    print(f"\nTotal: Found {result['found']}, Saved {result['saved']} new items")
