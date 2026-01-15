#!/usr/bin/env python3
"""
GitHub Advanced Crawler - расширенный мониторинг репозиториев
- Отслеживание по звездам и активности
- Поиск "восходящих звезд" (молодые быстрорастущие проекты)
- Watchlist для интересных проектов
"""
import sqlite3
import json
import urllib.request
import ssl
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "knowledge" / "news.db"
ssl._create_default_https_context = ssl._create_unverified_context

# Категории поиска
SEARCH_QUERIES = [
    # MCP и агенты
    {"q": "mcp model context protocol", "category": "mcp"},
    {"q": "anthropic claude agent", "category": "claude"},
    {"q": "llm agent autonomous", "category": "agents"},
    {"q": "agentic ai framework", "category": "agentic"},
    # Протоколы
    {"q": "agent to agent protocol a2a", "category": "protocols"},
    {"q": "universal commerce protocol", "category": "protocols"},
    # Инструменты
    {"q": "claude code cli", "category": "tools"},
    {"q": "llm coding assistant", "category": "tools"},
]

# Минимальные пороги
MIN_STARS_ESTABLISHED = 100      # Для "проверенных" проектов
MIN_STARS_RISING = 10            # Для "восходящих звезд"
MAX_AGE_RISING_DAYS = 90         # Максимальный возраст для "восходящих"
MIN_STARS_PER_DAY_RISING = 0.5   # Минимум звезд в день для "восходящих"

def init_watchlist_table():
    """Initialize watchlist table"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS github_watchlist (
        id INTEGER PRIMARY KEY,
        repo_name TEXT UNIQUE,
        url TEXT,
        description TEXT,
        stars INTEGER,
        forks INTEGER,
        language TEXT,
        category TEXT,
        status TEXT DEFAULT 'watching',
        is_rising_star BOOLEAN DEFAULT 0,
        stars_per_day REAL,
        created_at TEXT,
        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS github_history (
        id INTEGER PRIMARY KEY,
        repo_name TEXT,
        stars INTEGER,
        forks INTEGER,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def fetch_github(url):
    """Fetch GitHub API with rate limit handling"""
    headers = {
        "User-Agent": "AGI-News-Agent/1.0",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"GitHub API error: {e}")
        return None

def calculate_growth_rate(repo):
    """Calculate stars per day since creation"""
    created = datetime.strptime(repo['created_at'][:10], '%Y-%m-%d')
    age_days = (datetime.now() - created).days or 1
    stars_per_day = repo['stargazers_count'] / age_days
    return stars_per_day, age_days

def is_rising_star(repo):
    """Check if repo is a rising star"""
    stars_per_day, age_days = calculate_growth_rate(repo)
    stars = repo['stargazers_count']
    
    return (
        age_days <= MAX_AGE_RISING_DAYS and
        stars >= MIN_STARS_RISING and
        stars_per_day >= MIN_STARS_PER_DAY_RISING
    )

def search_github_repos():
    """Search GitHub for relevant repos"""
    all_repos = []
    
    for search in SEARCH_QUERIES:
        query = search["q"].replace(" ", "+")
        category = search["category"]
        
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=30"
        data = fetch_github(url)
        
        if not data or "items" not in data:
            continue
        
        for repo in data["items"]:
            stars_per_day, age_days = calculate_growth_rate(repo)
            rising = is_rising_star(repo)
            
            all_repos.append({
                "name": repo["full_name"],
                "url": repo["html_url"],
                "description": (repo.get("description") or "")[:500],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language"),
                "category": category,
                "created_at": repo["created_at"],
                "age_days": age_days,
                "stars_per_day": round(stars_per_day, 2),
                "is_rising_star": rising,
                "topics": repo.get("topics", [])
            })
    
    # Remove duplicates
    seen = set()
    unique = []
    for r in all_repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    
    return unique

def update_watchlist(repos):
    """Update watchlist with new/updated repos"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    new_repos = 0
    updated = 0
    rising_stars = []
    high_value = []
    
    for repo in repos:
        # Check if exists
        c.execute("SELECT stars FROM github_watchlist WHERE repo_name = ?", (repo["name"],))
        existing = c.fetchone()
        
        if existing:
            old_stars = existing[0]
            # Record history
            c.execute('''INSERT INTO github_history (repo_name, stars, forks)
                         VALUES (?, ?, ?)''', (repo["name"], repo["stars"], repo["forks"]))
            
            # Update
            c.execute('''UPDATE github_watchlist SET
                         stars = ?, forks = ?, stars_per_day = ?,
                         is_rising_star = ?, last_updated = CURRENT_TIMESTAMP
                         WHERE repo_name = ?''',
                      (repo["stars"], repo["forks"], repo["stars_per_day"],
                       repo["is_rising_star"], repo["name"]))
            updated += 1
            
            # Check for significant growth
            if repo["stars"] > old_stars * 1.1:  # 10% growth
                high_value.append(repo)
        else:
            # New repo
            c.execute('''INSERT INTO github_watchlist 
                         (repo_name, url, description, stars, forks, language,
                          category, is_rising_star, stars_per_day, created_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (repo["name"], repo["url"], repo["description"],
                       repo["stars"], repo["forks"], repo["language"],
                       repo["category"], repo["is_rising_star"],
                       repo["stars_per_day"], repo["created_at"]))
            new_repos += 1
            
            # Track rising stars
            if repo["is_rising_star"]:
                rising_stars.append(repo)
            
            # Track high-value established repos
            if repo["stars"] >= MIN_STARS_ESTABLISHED:
                high_value.append(repo)
    
    conn.commit()
    conn.close()
    
    return {
        "new_repos": new_repos,
        "updated": updated,
        "rising_stars": rising_stars,
        "high_value": high_value
    }

def get_watchlist_summary():
    """Get watchlist summary"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Top by stars
    c.execute('''SELECT repo_name, stars, stars_per_day, category, is_rising_star
                 FROM github_watchlist ORDER BY stars DESC LIMIT 10''')
    top_stars = c.fetchall()
    
    # Rising stars
    c.execute('''SELECT repo_name, stars, stars_per_day, category, created_at
                 FROM github_watchlist WHERE is_rising_star = 1
                 ORDER BY stars_per_day DESC LIMIT 10''')
    rising = c.fetchall()
    
    # By category
    c.execute('''SELECT category, COUNT(*), AVG(stars) FROM github_watchlist
                 GROUP BY category ORDER BY AVG(stars) DESC''')
    categories = c.fetchall()
    
    conn.close()
    
    return {
        "top_by_stars": top_stars,
        "rising_stars": rising,
        "by_category": categories
    }

def crawl_and_update():
    """Main crawl function"""
    print("Initializing tables...")
    init_watchlist_table()
    
    print("Searching GitHub...")
    repos = search_github_repos()
    print(f"Found {len(repos)} repos")
    
    print("Updating watchlist...")
    result = update_watchlist(repos)
    
    print(f"New: {result['new_repos']}, Updated: {result['updated']}")
    print(f"Rising stars: {len(result['rising_stars'])}")
    print(f"High value: {len(result['high_value'])}")
    
    return result

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "crawl"
    
    if cmd == "crawl":
        result = crawl_and_update()
        print(json.dumps({
            "new": result["new_repos"],
            "updated": result["updated"],
            "rising_count": len(result["rising_stars"]),
            "high_value_count": len(result["high_value"])
        }, indent=2))
    elif cmd == "summary":
        summary = get_watchlist_summary()
        print("\n=== TOP BY STARS ===")
        for r in summary["top_by_stars"]:
            rising = "🚀" if r[4] else ""
            print(f"  [{r[1]:>5}⭐ {r[2]:.1f}/day] {r[0]} ({r[3]}) {rising}")
        
        print("\n=== RISING STARS ===")
        for r in summary["rising_stars"]:
            print(f"  [{r[1]:>4}⭐ {r[2]:.1f}/day] {r[0]} ({r[3]})")
        
        print("\n=== BY CATEGORY ===")
        for c in summary["by_category"]:
            print(f"  {c[0]}: {c[1]} repos, avg {c[2]:.0f}⭐")
    elif cmd == "rising":
        summary = get_watchlist_summary()
        for r in summary["rising_stars"]:
            print(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}")
