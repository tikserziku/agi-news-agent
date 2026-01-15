#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(__file__).parent.parent / "knowledge" / "news.db"
ALERTS = Path(__file__).parent.parent / "logs" / "alerts.json"

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/alerts':
            self.json(self.alerts())
        elif self.path == '/api/rising':
            self.json(self.rising())
        else:
            self.html(self.dashboard())
    
    def json(self, d):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    
    def html(self, h):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(h.encode())
    
    def alerts(self):
        try:
            with open(ALERTS) as f: return json.load(f)
        except: return []
    
    def rising(self):
        try:
            c = sqlite3.connect(DB).cursor()
            c.execute('SELECT repo_name,stars,stars_per_day,url FROM github_watchlist WHERE category IN ("rising","hot") ORDER BY stars_per_day DESC LIMIT 20')
            return [{"name":r[0],"stars":r[1],"growth":r[2],"url":r[3]} for r in c.fetchall()]
        except: return []
    
    def stats(self):
        try:
            c = sqlite3.connect(DB).cursor()
            s = {}
            for t in ["news","technologies","github_watchlist"]:
                try: c.execute(f"SELECT COUNT(*) FROM {t}"); s[t]=c.fetchone()[0]
                except: s[t]=0
            return s
        except: return {}
    
    def dashboard(self):
        s = self.stats()
        a = self.alerts()[:10]
        r = self.rising()[:10]
        
        ah = "".join(f'<div style="background:#1a1a2e;padding:15px;margin:10px 0;border-radius:8px;border-left:4px solid {"#f44" if x.get("priority")=="high" else "#0f8"}"><b>{x.get("title","")}</b><br><small>{x.get("message","")[:150]}</small><br><a href="{x.get("url","")}" style="color:#0af">{x.get("url","")[:50]}</a></div>' for x in a)
        rh = "".join(f'<div style="background:#1a2a1a;padding:15px;margin:10px 0;border-radius:8px"><b>{x["name"]}</b> - {x["stars"]} stars ({x["growth"]}/day)<br><a href="{x["url"]}" style="color:#0af">{x["url"][:50]}</a></div>' for x in r)
        
        return f'''<!DOCTYPE html><html><head><title>AGI Alerts</title><meta charset="utf-8">
<style>body{{font-family:system-ui;background:#0f0f0f;color:#e0e0e0;padding:20px}}h1{{color:#0f8}}h2{{color:#0af;margin:20px 0}}.stats{{background:#1a1a1a;padding:15px;border-radius:8px;margin-bottom:20px}}.stats span{{margin-right:20px}}</style></head>
<body><h1>AGI News Agent - Alerts</h1>
<div class="stats"><span>News: {s.get("news",0)}</span><span>Tech: {s.get("technologies",0)}</span><span>Watching: {s.get("github_watchlist",0)}</span></div>
<h2>Rising Stars</h2>{rh or "<p>No data</p>"}
<h2>Recent Alerts</h2>{ah or "<p>No alerts</p>"}
<p style="color:#666;margin-top:30px">Updated: {datetime.now()}</p></body></html>'''
    
    def log_message(self, *a): pass

if __name__ == "__main__":
    print("Starting on :3458")
    HTTPServer(('0.0.0.0', 3458), H).serve_forever()
