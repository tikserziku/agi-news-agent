#!/usr/bin/env python3
"""
AGI News Agent v2.0 - Self-Learning System
Полный цикл: Crawl -> Analyze -> Architect -> Notify
"""
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "knowledge" / "news.db"

sys.path.insert(0, str(BASE_DIR))
from crawlers.news_crawler import crawl_all as crawl_news
from crawlers.github_advanced import crawl_and_update as crawl_github, get_watchlist_summary
from crawlers.blog_crawler import crawl_and_save as crawl_blogs
from analyzer.news_analyzer import analyze_news, get_high_relevance_news, get_discovered_technologies
from architect.planner import plan_all_technologies, show_plans
from notifier import check_and_notify, get_pending_notifications

def log_run(action, result):
    """Log agent run"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO agent_actions (action_type, description, output_data, success)
                 VALUES (?, ?, ?, ?)''',
              (action, f"Agent run: {action}", json.dumps(result), True))
    conn.commit()
    conn.close()

def run_full_cycle():
    """Run complete agent cycle"""
    print("=" * 60)
    print(f"AGI NEWS AGENT v2.0 - Full Cycle")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {}
    
    # Step 1: Crawl all sources
    print("\n[1/5] CRAWLING SOURCES...")
    
    print("  → HackerNews...")
    news_result = crawl_news()
    results["news"] = news_result
    print(f"     Found: {news_result['found']}, Saved: {news_result['saved']}")
    
    print("  → Blogs (Anthropic, Google, OpenAI)...")
    blog_result = crawl_blogs()
    results["blogs"] = blog_result
    print(f"     Found: {blog_result['total_found']}, Saved: {blog_result['saved']}")
    
    print("  → GitHub Advanced...")
    try:
        github_result = crawl_github()
        results["github"] = {
            "new": github_result["new_repos"],
            "updated": github_result["updated"],
            "rising_stars": len(github_result["rising_stars"]),
            "high_value": len(github_result["high_value"])
        }
        print(f"     New: {github_result['new_repos']}, Rising: {len(github_result['rising_stars'])}")
    except Exception as e:
        print(f"     GitHub error: {e}")
        results["github"] = {"error": str(e)}
    
    # Step 2: Analyze
    print("\n[2/5] ANALYZING...")
    analyze_result = analyze_news()
    results["analyze"] = analyze_result
    print(f"     Analyzed: {analyze_result['analyzed']}")
    print(f"     Knowledge: {analyze_result['knowledge_extracted']}")
    print(f"     Technologies: {analyze_result['new_technologies']}")
    
    # Step 3: Plan
    print("\n[3/5] PLANNING...")
    plan_result = plan_all_technologies()
    results["plan"] = plan_result
    print(f"     Planned: {plan_result['planned']}")
    
    # Step 4: Notify
    print("\n[4/5] SENDING NOTIFICATIONS...")
    notify_result = check_and_notify()
    results["notify"] = notify_result
    print(f"     Notified: {notify_result.get('notified', False)}")
    if notify_result.get("channels"):
        print(f"     Channels: {', '.join(notify_result['channels'])}")
    
    # Step 5: Summary
    print("\n[5/5] GENERATING SUMMARY...")
    
    print("\n" + "=" * 60)
    print("CYCLE COMPLETE")
    print("=" * 60)
    
    log_run("full_cycle_v2", results)
    return results

def get_status():
    """Get full system status"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    status = {
        "agent": "AGI News Agent v2.0",
        "timestamp": datetime.now().isoformat(),
        "tables": {}
    }
    
    for table in ["news", "knowledge", "technologies", "agent_actions", "github_watchlist"]:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            status["tables"][table] = c.fetchone()[0]
        except:
            status["tables"][table] = 0
    
    # GitHub summary
    try:
        c.execute("SELECT COUNT(*) FROM github_watchlist WHERE is_rising_star = 1")
        status["rising_stars"] = c.fetchone()[0]
    except:
        status["rising_stars"] = 0
    
    # Recent actions
    c.execute('''SELECT action_type, executed_at FROM agent_actions 
                 ORDER BY executed_at DESC LIMIT 3''')
    status["recent_actions"] = [{"action": r[0], "at": r[1]} for r in c.fetchall()]
    
    conn.close()
    return status

def generate_report():
    """Generate comprehensive report"""
    print("\n" + "=" * 70)
    print("                    AGI NEWS AGENT - FULL REPORT")
    print("=" * 70)
    
    # Status
    status = get_status()
    print(f"\n📊 DATABASE STATUS:")
    print(f"   News items: {status['tables'].get('news', 0)}")
    print(f"   Knowledge items: {status['tables'].get('knowledge', 0)}")
    print(f"   Technologies: {status['tables'].get('technologies', 0)}")
    print(f"   GitHub repos: {status['tables'].get('github_watchlist', 0)}")
    print(f"   Rising stars: {status.get('rising_stars', 0)}")
    
    # GitHub summary
    print("\n" + "-" * 70)
    print("🐙 GITHUB WATCHLIST")
    print("-" * 70)
    try:
        summary = get_watchlist_summary()
        
        print("\n⭐ TOP BY STARS:")
        for r in summary["top_by_stars"][:5]:
            rising = " 🚀" if r[4] else ""
            print(f"   [{r[1]:>6}⭐ {r[2]:>5.1f}/day] {r[0][:40]} ({r[3]}){rising}")
        
        print("\n🚀 RISING STARS (молодые быстрорастущие):")
        for r in summary["rising_stars"][:5]:
            print(f"   [{r[1]:>5}⭐ {r[2]:>5.1f}/day] {r[0][:40]} ({r[3]})")
    except Exception as e:
        print(f"   Error: {e}")
    
    # High relevance news
    print("\n" + "-" * 70)
    print("📰 HIGH RELEVANCE NEWS")
    print("-" * 70)
    news = get_high_relevance_news(40)
    for n in news[:5]:
        print(f"   [{n[3]:>3}] {n[1]}: {n[2][:45]}...")
    
    # Technologies
    print("\n" + "-" * 70)
    print("🔧 DISCOVERED TECHNOLOGIES")
    print("-" * 70)
    techs = get_discovered_technologies()
    for t in techs[:5]:
        print(f"   [{t[2]:>10}] {t[0]}: {t[1][:40]}...")
    
    # Pending notifications
    print("\n" + "-" * 70)
    print("🔔 PENDING NOTIFICATIONS")
    print("-" * 70)
    notifications = get_pending_notifications()
    if notifications:
        latest = notifications[-1]
        print(f"   Last: {latest.get('timestamp', 'N/A')}")
        if latest.get("rising_stars"):
            print(f"   Rising stars: {len(latest['rising_stars'])}")
        if latest.get("high_value"):
            print(f"   High value: {len(latest['high_value'])}")
    else:
        print("   No pending notifications")
    
    print("\n" + "=" * 70)

def show_rising_stars():
    """Show only rising stars"""
    summary = get_watchlist_summary()
    print("\n🚀 RISING STARS - Молодые быстрорастущие проекты")
    print("=" * 60)
    for r in summary["rising_stars"]:
        print(f"\n📦 {r[0]}")
        print(f"   ⭐ {r[1]} stars ({r[2]:.1f} per day)")
        print(f"   📂 Category: {r[3]}")
        print(f"   📅 Created: {r[4][:10] if r[4] else 'N/A'}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "run":
        result = run_full_cycle()
        print(json.dumps(result, indent=2))
    elif cmd == "status":
        status = get_status()
        print(json.dumps(status, indent=2))
    elif cmd == "report":
        generate_report()
    elif cmd == "rising":
        show_rising_stars()
    elif cmd == "notify":
        result = check_and_notify()
        print(json.dumps(result, indent=2))
    else:
        print(f"AGI News Agent v2.0")
        print(f"Commands: run, status, report, rising, notify")
