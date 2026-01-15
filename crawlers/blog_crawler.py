#!/usr/bin/env python3
"""
Blog Crawler - мониторинг блогов Anthropic и Google AI
"""
import sqlite3
import json
import urllib.request
import ssl
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"
ssl._create_default_https_context = ssl._create_unverified_context

BLOG_SOURCES = {
    "anthropic": {
        "rss": "https://www.anthropic.com/rss.xml",
        "keywords": ["claude", "mcp", "agent", "model", "safety", "api"]
    },
    "google_ai": {
        "rss": "https://blog.google/technology/ai/rss/",
        "keywords": ["gemini", "agent", "ai", "bard", "palm", "vertex"]
    },
    "openai": {
        "rss": "https://openai.com/blog/rss.xml",
        "keywords": ["gpt", "agent", "api", "chatgpt", "assistant"]
    }
}

def fetch_url(url):
    """Fetch URL content"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AGI-News-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_rss(xml_content, source_name):
    """Simple RSS parser"""
    items = []
    
    # Extract items using regex
    item_pattern = r'<item>(.*?)</item>'
    title_pattern = r'<title>(.*?)</title>'
    link_pattern = r'<link>(.*?)</link>'
    desc_pattern = r'<description>(.*?)</description>'
    pubdate_pattern = r'<pubDate>(.*?)</pubDate>'
    
    for item_match in re.finditer(item_pattern, xml_content, re.DOTALL):
        item_content = item_match.group(1)
        
        title = re.search(title_pattern, item_content, re.DOTALL)
        link = re.search(link_pattern, item_content, re.DOTALL)
        desc = re.search(desc_pattern, item_content, re.DOTALL)
        pubdate = re.search(pubdate_pattern, item_content, re.DOTALL)
        
        if title and link:
            # Clean CDATA
            title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title.group(1)).strip()
            link_text = link.group(1).strip()
            desc_text = ""
            if desc:
                desc_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc.group(1))
                desc_text = re.sub(r'<[^>]+>', '', desc_text)[:500]
            
            items.append({
                "source": source_name,
                "title": title_text,
                "url": link_text,
                "content": desc_text,
                "pubdate": pubdate.group(1) if pubdate else None
            })
    
    return items[:20]  # Limit to 20 items

def crawl_blogs():
    """Crawl all blog sources"""
    all_posts = []
    
    for source_name, config in BLOG_SOURCES.items():
        print(f"Crawling {source_name}...")
        content = fetch_url(config["rss"])
        
        if not content:
            continue
        
        posts = parse_rss(content, source_name)
        
        # Filter by keywords
        keywords = config["keywords"]
        filtered = []
        for post in posts:
            text = f"{post['title']} {post['content']}".lower()
            if any(kw in text for kw in keywords):
                post["matched_keywords"] = [kw for kw in keywords if kw in text]
                filtered.append(post)
        
        all_posts.extend(filtered)
        print(f"  Found {len(filtered)} relevant posts")
    
    return all_posts

def save_blog_posts(posts):
    """Save posts to news table"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    saved = 0
    for post in posts:
        try:
            c.execute('''INSERT OR IGNORE INTO news (source, title, content, url)
                         VALUES (?, ?, ?, ?)''',
                      (f"blog_{post['source']}", post["title"], 
                       post["content"], post["url"]))
            if c.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"Error saving: {e}")
    
    conn.commit()
    conn.close()
    return saved

def crawl_and_save():
    """Main function"""
    posts = crawl_blogs()
    saved = save_blog_posts(posts)
    
    return {
        "total_found": len(posts),
        "saved": saved,
        "sources": list(set(p["source"] for p in posts))
    }

if __name__ == "__main__":
    result = crawl_and_save()
    print(json.dumps(result, indent=2))
