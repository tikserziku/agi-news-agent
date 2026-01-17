#!/usr/bin/env python3
"""
Web API для AGI News Agent
Эндпоинты для просмотра находок и управления агентом
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB_PATH = Path(__file__).parent / "knowledge" / "news.db"
NOTIFY_PATH = Path(__file__).parent / "notifications.json"

class AgentAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
    
    def _send_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/':
            self._serve_dashboard()
        elif path == '/api/status':
            self._api_status()
        elif path == '/api/rising':
            self._api_rising_stars()
        elif path == '/api/news':
            self._api_news(query)
        elif path == '/api/notifications':
            self._api_notifications()
        elif path == '/api/watchlist':
            self._api_watchlist(query)
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def _serve_dashboard(self):
        html = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AGI News Agent - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: #0d1117; color: #c9d1d9; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #58a6ff; margin-bottom: 20px; }
        h2 { color: #8b949e; margin: 20px 0 10px; font-size: 1.2em; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; 
                padding: 15px; margin-bottom: 15px; }
        .stat { display: inline-block; margin-right: 20px; }
        .stat-value { font-size: 24px; color: #58a6ff; font-weight: bold; }
        .stat-label { color: #8b949e; font-size: 12px; }
        .repo { padding: 10px 0; border-bottom: 1px solid #30363d; }
        .repo:last-child { border-bottom: none; }
        .repo-name { color: #58a6ff; text-decoration: none; }
        .repo-name:hover { text-decoration: underline; }
        .stars { color: #f0c14b; }
        .rising { background: #238636; color: white; padding: 2px 8px; border-radius: 12px; 
                  font-size: 11px; margin-left: 8px; }
        .category { background: #21262d; padding: 2px 8px; border-radius: 4px; 
                    font-size: 11px; color: #8b949e; }
        .refresh-btn { background: #238636; color: white; border: none; padding: 10px 20px;
                       border-radius: 6px; cursor: pointer; margin-bottom: 20px; }
        .refresh-btn:hover { background: #2ea043; }
        .news-item { padding: 8px 0; border-bottom: 1px solid #30363d; }
        .news-score { background: #21262d; padding: 2px 6px; border-radius: 4px; 
                      font-size: 11px; margin-right: 8px; }
        #loading { color: #8b949e; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AGI News Agent Dashboard</h1>
        <button class="refresh-btn" onclick="loadAll()">🔄 Обновить</button>
        
        <div id="status" class="card">
            <div id="loading">Загрузка...</div>
        </div>
        
        <h2>🚀 Восходящие звёзды (быстрорастущие проекты)</h2>
        <div id="rising" class="card"></div>
        
        <h2>⭐ Топ проекты по звёздам</h2>
        <div id="watchlist" class="card"></div>
        
        <h2>📰 Последние релевантные новости</h2>
        <div id="news" class="card"></div>
    </div>
    
    <script>
        async function fetchJSON(url) {
            const res = await fetch(url);
            return res.json();
        }
        
        async function loadStatus() {
            const data = await fetchJSON('/api/status');
            document.getElementById('status').innerHTML = `
                <div class="stat"><div class="stat-value">${data.github_repos || 0}</div><div class="stat-label">GitHub Repos</div></div>
                <div class="stat"><div class="stat-value">${data.rising_stars || 0}</div><div class="stat-label">Rising Stars</div></div>
                <div class="stat"><div class="stat-value">${data.news || 0}</div><div class="stat-label">News Items</div></div>
                <div class="stat"><div class="stat-value">${data.technologies || 0}</div><div class="stat-label">Technologies</div></div>
            `;
        }
        
        async function loadRising() {
            const data = await fetchJSON('/api/rising');
            if (!data.length) {
                document.getElementById('rising').innerHTML = '<div style="color:#8b949e">Нет данных</div>';
                return;
            }
            document.getElementById('rising').innerHTML = data.map(r => `
                <div class="repo">
                    <a href="${r.url}" target="_blank" class="repo-name">${r.name}</a>
                    <span class="rising">🚀 Rising</span>
                    <span class="category">${r.category}</span>
                    <div style="margin-top:5px">
                        <span class="stars">⭐ ${r.stars}</span>
                        <span style="color:#8b949e; margin-left:10px">${r.stars_per_day} stars/day</span>
                    </div>
                    <div style="color:#8b949e; font-size:12px; margin-top:5px">${r.description || ''}</div>
                </div>
            `).join('');
        }
        
        async function loadWatchlist() {
            const data = await fetchJSON('/api/watchlist?limit=10');
            document.getElementById('watchlist').innerHTML = data.map(r => `
                <div class="repo">
                    <a href="${r.url}" target="_blank" class="repo-name">${r.name}</a>
                    ${r.is_rising ? '<span class="rising">🚀</span>' : ''}
                    <span class="category">${r.category}</span>
                    <div style="margin-top:5px">
                        <span class="stars">⭐ ${r.stars}</span>
                        <span style="color:#8b949e; margin-left:10px">${r.stars_per_day} /day</span>
                    </div>
                </div>
            `).join('');
        }
        
        async function loadNews() {
            const data = await fetchJSON('/api/news?limit=10');
            document.getElementById('news').innerHTML = data.map(n => `
                <div class="news-item">
                    <span class="news-score">${n.score}</span>
                    <a href="${n.url}" target="_blank" class="repo-name">${n.title}</a>
                    <span class="category">${n.source}</span>
                </div>
            `).join('');
        }
        
        function loadAll() {
            loadStatus();
            loadRising();
            loadWatchlist();
            loadNews();
        }
        
        loadAll();
        setInterval(loadAll, 60000); // Refresh every minute
    </script>
</body>
</html>'''
        self._send_html(html)
    
    def _api_status(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        status = {}
        
        try:
            c.execute("SELECT COUNT(*) FROM github_watchlist")
            status["github_repos"] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM github_watchlist WHERE is_rising_star = 1")
            status["rising_stars"] = c.fetchone()[0]
        except: pass
        
        try:
            c.execute("SELECT COUNT(*) FROM news")
            status["news"] = c.fetchone()[0]
        except: pass
        
        try:
            c.execute("SELECT COUNT(*) FROM technologies")
            status["technologies"] = c.fetchone()[0]
        except: pass
        
        conn.close()
        self._send_json(status)
    
    def _api_rising_stars(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT repo_name, url, stars, stars_per_day, category, description
                     FROM github_watchlist WHERE is_rising_star = 1
                     ORDER BY stars_per_day DESC LIMIT 20''')
        results = [{"name": r[0], "url": r[1], "stars": r[2], 
                    "stars_per_day": r[3], "category": r[4], "description": r[5]}
                   for r in c.fetchall()]
        conn.close()
        self._send_json(results)
    
    def _api_watchlist(self, query):
        limit = int(query.get('limit', [20])[0])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT repo_name, url, stars, stars_per_day, category, is_rising_star
                     FROM github_watchlist ORDER BY stars DESC LIMIT ?''', (limit,))
        results = [{"name": r[0], "url": r[1], "stars": r[2], 
                    "stars_per_day": r[3], "category": r[4], "is_rising": bool(r[5])}
                   for r in c.fetchall()]
        conn.close()
        self._send_json(results)
    
    def _api_news(self, query):
        limit = int(query.get('limit', [20])[0])
        min_score = int(query.get('min_score', [30])[0])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT title, url, relevance_score, source FROM news
                     WHERE relevance_score >= ? ORDER BY relevance_score DESC LIMIT ?''',
                  (min_score, limit))
        results = [{"title": r[0], "url": r[1], "score": r[2], "source": r[3]}
                   for r in c.fetchall()]
        conn.close()
        self._send_json(results)
    
    def _api_notifications(self):
        if NOTIFY_PATH.exists():
            with open(NOTIFY_PATH) as f:
                self._send_json(json.load(f))
        else:
            self._send_json([])
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def run_server(port=3457):
    server = HTTPServer(('0.0.0.0', port), AgentAPIHandler)
    print(f"AGI Agent Web API running on http://0.0.0.0:{port}")
    server.serve_forever()

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3457
    run_server(port)
