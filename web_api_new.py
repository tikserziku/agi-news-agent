#!/usr/bin/env python3
"""
AGI Dashboard v3 - Extended System Monitoring with Navigation
Sections: API Keys, Errors, System, Learning, Services
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, sqlite3, subprocess, os
from pathlib import Path
from datetime import datetime

DB = Path(__file__).parent.parent / "knowledge" / "news.db"
ALERTS = Path(__file__).parent.parent / "logs" / "alerts.json"
KEYS_FILE = Path.home() / ".keys" / "keys.json"
KNOWLEDGE_FILE = Path.home() / "agent-memory" / "internal-knowledge.json"

# Menu items with pages
MENU_ITEMS = [
    {"id": "dashboard", "icon": "🏠", "name": "Dashboard", "path": "/"},
    {"id": "system", "icon": "💾", "name": "System", "path": "/system"},
    {"id": "services", "icon": "🤖", "name": "Services", "path": "/services"},
    {"id": "keys", "icon": "🔑", "name": "API Keys", "path": "/keys"},
    {"id": "learning", "icon": "🧠", "name": "Learning", "path": "/learning"},
    {"id": "errors", "icon": "❌", "name": "Errors", "path": "/errors"},
    {"id": "rising", "icon": "⭐", "name": "Rising", "path": "/rising"},
    {"id": "alerts", "icon": "🔔", "name": "Alerts", "path": "/alerts"},
]

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]

        # API endpoints
        if path == '/api/alerts': self.json(self.alerts())
        elif path == '/api/rising': self.json(self.rising())
        elif path == '/api/system': self.json(self.system_stats())
        elif path == '/api/services': self.json(self.services())
        elif path == '/api/keys': self.json(self.api_keys())
        elif path == '/api/learning': self.json(self.learning())
        elif path == '/api/errors': self.json(self.errors())
        # Page routes
        elif path == '/system': self.html(self.page_system())
        elif path == '/services': self.html(self.page_services())
        elif path == '/keys': self.html(self.page_keys())
        elif path == '/learning': self.html(self.page_learning())
        elif path == '/errors': self.html(self.page_errors())
        elif path == '/rising': self.html(self.page_rising())
        elif path == '/alerts': self.html(self.page_alerts())
        else: self.html(self.dashboard())

    def json(self, d):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(d, default=str).encode())

    def html(self, h):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
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

    def system_stats(self):
        try:
            mem = subprocess.run(['free', '-m'], capture_output=True, text=True)
            mem_lines = mem.stdout.strip().split('\n')
            if len(mem_lines) > 1:
                parts = mem_lines[1].split()
                total, used, free = int(parts[1]), int(parts[2]), int(parts[3])
                mem_percent = round(used / total * 100, 1)
            else:
                total, used, free, mem_percent = 0, 0, 0, 0

            disk = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            disk_lines = disk.stdout.strip().split('\n')
            if len(disk_lines) > 1:
                parts = disk_lines[1].split()
                disk_total, disk_used, disk_free, disk_percent = parts[1], parts[2], parts[3], parts[4]
            else:
                disk_total, disk_used, disk_free, disk_percent = '0', '0', '0', '0%'

            load = subprocess.run(['cat', '/proc/loadavg'], capture_output=True, text=True)
            load_avg = load.stdout.strip().split()[:3] if load.stdout else ['0', '0', '0']

            uptime = subprocess.run(['uptime', '-p'], capture_output=True, text=True)

            return {
                "memory": {"total_mb": total, "used_mb": used, "free_mb": free, "percent": mem_percent},
                "disk": {"total": disk_total, "used": disk_used, "free": disk_free, "percent": disk_percent},
                "load": load_avg,
                "uptime": uptime.stdout.strip() if uptime.stdout else "unknown"
            }
        except Exception as e:
            return {"error": str(e)}

    def services(self):
        services = []
        try:
            pm2 = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=5)
            if pm2.returncode == 0:
                pm2_list = json.loads(pm2.stdout)
                for svc in pm2_list:
                    services.append({
                        "name": svc.get("name", "unknown"),
                        "status": svc.get("pm2_env", {}).get("status", "unknown"),
                        "pid": svc.get("pid", 0),
                        "memory": round(svc.get("monit", {}).get("memory", 0) / 1024 / 1024, 1),
                        "cpu": svc.get("monit", {}).get("cpu", 0),
                        "restarts": svc.get("pm2_env", {}).get("restart_time", 0),
                        "type": "pm2"
                    })
        except: pass

        try:
            ps = subprocess.run(['pgrep', '-a', 'python3'], capture_output=True, text=True, timeout=5)
            if ps.returncode == 0:
                for line in ps.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(None, 1)
                        if len(parts) >= 2:
                            pid, cmd = parts
                            name = cmd.split('/')[-1].replace('.py', '')[:30]
                            if 'python3' not in name and name not in [s['name'] for s in services]:
                                services.append({
                                    "name": name,
                                    "status": "online",
                                    "pid": int(pid),
                                    "type": "python"
                                })
        except: pass
        return services

    def api_keys(self):
        keys = []
        try:
            if KEYS_FILE.exists():
                with open(KEYS_FILE) as f:
                    data = json.load(f)
                for service, info in data.items():
                    key_file = Path.home() / ".keys" / info.get("keys", [{}])[0].get("file", "")
                    keys.append({
                        "service": service,
                        "active": info.get("active", ""),
                        "status": "ok" if key_file.exists() else "missing",
                        "key_preview": self._key_preview(key_file)
                    })
        except Exception as e:
            keys.append({"error": str(e)})
        return keys

    def _key_preview(self, key_file):
        try:
            if key_file.exists():
                key = key_file.read_text().strip()
                if len(key) > 10:
                    return f"{key[:4]}...{key[-4:]}"
        except: pass
        return "***"

    def learning(self):
        try:
            if KNOWLEDGE_FILE.exists():
                with open(KNOWLEDGE_FILE) as f:
                    data = json.load(f)
                projects = data.get("projects", {})
                return {
                    "last_updated": data.get("last_updated", "never"),
                    "projects_learned": len(projects),
                    "total_functions": sum(len(p.get("functions", [])) for p in projects.values()),
                    "total_classes": sum(len(p.get("classes", [])) for p in projects.values()),
                    "concepts": len(data.get("concepts", [])),
                    "projects": list(projects.keys()),
                    "details": {k: {"files": len(v.get("files", [])), "functions": len(v.get("functions", []))} for k, v in projects.items()}
                }
        except Exception as e:
            return {"error": str(e)}
        return {"projects_learned": 0}

    def errors(self):
        errors = []
        log_paths = [
            Path.home() / ".pm2" / "logs",
            Path.home() / "agi-news-agent" / "logs",
            Path.home() / "claude-mailbox"
        ]
        for log_dir in log_paths:
            try:
                if log_dir.exists():
                    for log_file in log_dir.glob("*error*.log"):
                        try:
                            lines = log_file.read_text().strip().split('\n')[-10:]
                            for line in lines:
                                if line.strip() and ('error' in line.lower() or 'exception' in line.lower()):
                                    errors.append({
                                        "source": log_file.name,
                                        "message": line[:200],
                                        "time": datetime.now().isoformat()
                                    })
                        except: pass
            except: pass
        try:
            journal = subprocess.run(
                ['journalctl', '--since', '1 hour ago', '-p', 'err', '--no-pager', '-n', '10'],
                capture_output=True, text=True, timeout=5
            )
            if journal.returncode == 0:
                for line in journal.stdout.strip().split('\n')[-5:]:
                    if line.strip():
                        errors.append({"source": "system", "message": line[:200]})
        except: pass
        return errors[-20:]

    def base_html(self, title, content, active="dashboard"):
        menu_html = "".join(
            f'<a href="{m["path"]}" class="menu-item {"active" if m["id"]==active else ""}">'
            f'{m["icon"]}<span>{m["name"]}</span></a>'
            for m in MENU_ITEMS
        )

        return f'''<!DOCTYPE html><html><head>
<title>{title} - AGI Dashboard</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:system-ui,-apple-system,sans-serif; background:#0a0a0f; color:#e0e0e0; }}
.layout {{ display:flex; min-height:100vh; }}
.sidebar {{ width:200px; background:#0f0f18; padding:15px; border-right:1px solid #222; position:fixed; height:100vh; overflow-y:auto; }}
.sidebar h1 {{ color:#0f8; font-size:1.2em; margin-bottom:20px; padding-bottom:10px; border-bottom:1px solid #222; }}
.menu-item {{ display:flex; align-items:center; gap:10px; padding:12px 15px; margin:5px 0; border-radius:8px; color:#888; text-decoration:none; transition:all 0.2s; }}
.menu-item:hover {{ background:#1a1a2a; color:#fff; }}
.menu-item.active {{ background:#0f8; color:#000; font-weight:600; }}
.menu-item span {{ font-size:0.9em; }}
.main {{ flex:1; margin-left:200px; padding:20px; }}
.header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:15px; border-bottom:1px solid #222; }}
.header h2 {{ color:#0af; font-size:1.4em; }}
.header .time {{ color:#666; font-size:0.85em; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:15px; }}
.section {{ background:#12121a; border-radius:10px; padding:15px; }}
.card {{ background:#1a1a2a; padding:12px; margin:8px 0; border-radius:8px; border-left:3px solid #333; }}
.card.online {{ border-color:#0f8; }}
.card.offline {{ border-color:#f44; }}
.card.ok {{ border-color:#0af; }}
.card.warn {{ border-color:#fa0; }}
.card.error {{ border-color:#f44; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:8px; }}
.dot.green {{ background:#0f8; }}
.dot.red {{ background:#f44; }}
.dot.yellow {{ background:#fa0; }}
.meter {{ height:8px; background:#333; border-radius:4px; margin-top:8px; }}
.meter-fill {{ height:100%; border-radius:4px; transition:width 0.3s; }}
.stats-row {{ display:flex; gap:15px; flex-wrap:wrap; margin-bottom:15px; }}
.stat-box {{ background:#1a1a2a; padding:15px 20px; border-radius:8px; min-width:120px; }}
.stat-box .value {{ font-size:1.5em; font-weight:bold; color:#0af; }}
.stat-box .label {{ font-size:0.8em; color:#666; margin-top:5px; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:12px; text-align:left; border-bottom:1px solid #222; }}
th {{ color:#0af; font-weight:500; }}
tr:hover {{ background:#1a1a2a; }}
small {{ color:#888; }}
.badge {{ display:inline-block; padding:3px 8px; border-radius:4px; font-size:0.75em; }}
.badge.green {{ background:#0f82; color:#0f8; }}
.badge.red {{ background:#f442; color:#f44; }}
@media (max-width: 768px) {{
    .sidebar {{ width:60px; padding:10px; }}
    .sidebar h1, .menu-item span {{ display:none; }}
    .main {{ margin-left:60px; }}
}}
</style></head>
<body>
<div class="layout">
    <nav class="sidebar">
        <h1>🤖 AGI</h1>
        {menu_html}
    </nav>
    <main class="main">
        <div class="header">
            <h2>{title}</h2>
            <span class="time">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
        {content}
    </main>
</div>
</body></html>'''

    def page_system(self):
        sys = self.system_stats()
        mem = sys.get("memory", {})
        disk = sys.get("disk", {})
        load = sys.get("load", ["0","0","0"])

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{mem.get("percent",0)}%</div><div class="label">Memory Used</div></div>
            <div class="stat-box"><div class="value">{disk.get("percent","0%")}</div><div class="label">Disk Used</div></div>
            <div class="stat-box"><div class="value">{load[0]}</div><div class="label">Load (1m)</div></div>
            <div class="stat-box"><div class="value">{load[1]}</div><div class="label">Load (5m)</div></div>
        </div>
        <div class="grid">
            <div class="section">
                <h3 style="color:#0af;margin-bottom:15px;">Memory</h3>
                <div class="card">
                    <b>{mem.get("used_mb",0)} MB</b> / {mem.get("total_mb",0)} MB
                    <div class="meter"><div class="meter-fill" style="width:{mem.get("percent",0)}%;background:linear-gradient(90deg,#0f8,#fa0);"></div></div>
                    <small>Free: {mem.get("free_mb",0)} MB</small>
                </div>
            </div>
            <div class="section">
                <h3 style="color:#0af;margin-bottom:15px;">Disk</h3>
                <div class="card">
                    <b>{disk.get("used","?")}</b> / {disk.get("total","?")}
                    <div class="meter"><div class="meter-fill" style="width:{disk.get("percent","0%").replace("%","")};background:linear-gradient(90deg,#0af,#f44);"></div></div>
                    <small>Free: {disk.get("free","?")}</small>
                </div>
            </div>
            <div class="section">
                <h3 style="color:#0af;margin-bottom:15px;">Uptime</h3>
                <div class="card">
                    <b>{sys.get("uptime","unknown")}</b>
                </div>
            </div>
        </div>'''
        return self.base_html("System", content, "system")

    def page_services(self):
        svcs = self.services()
        online = sum(1 for s in svcs if s.get("status") == "online")

        rows = "".join(f'''<tr>
            <td><span class="dot {"green" if s.get("status")=="online" else "red"}"></span>{s["name"]}</td>
            <td><span class="badge {"green" if s.get("status")=="online" else "red"}">{s.get("status","?")}</span></td>
            <td>{s.get("pid","-")}</td>
            <td>{s.get("memory","-")} MB</td>
            <td>{s.get("cpu","-")}%</td>
            <td>{s.get("type","")}</td>
        </tr>''' for s in svcs)

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{len(svcs)}</div><div class="label">Total Services</div></div>
            <div class="stat-box"><div class="value" style="color:#0f8">{online}</div><div class="label">Online</div></div>
            <div class="stat-box"><div class="value" style="color:#f44">{len(svcs)-online}</div><div class="label">Offline</div></div>
        </div>
        <div class="section">
            <table>
                <tr><th>Service</th><th>Status</th><th>PID</th><th>Memory</th><th>CPU</th><th>Type</th></tr>
                {rows}
            </table>
        </div>'''
        return self.base_html("Services", content, "services")

    def page_keys(self):
        keys = self.api_keys()

        rows = "".join(f'''<tr>
            <td><b>{k.get("service","?")}</b></td>
            <td>{k.get("active","")}</td>
            <td><span class="badge {"green" if k.get("status")=="ok" else "red"}">{k.get("status","?")}</span></td>
            <td><code>{k.get("key_preview","***")}</code></td>
        </tr>''' for k in keys)

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{len(keys)}</div><div class="label">Total Keys</div></div>
            <div class="stat-box"><div class="value" style="color:#0f8">{sum(1 for k in keys if k.get("status")=="ok")}</div><div class="label">Active</div></div>
        </div>
        <div class="section">
            <table>
                <tr><th>Service</th><th>Active Key</th><th>Status</th><th>Preview</th></tr>
                {rows}
            </table>
        </div>'''
        return self.base_html("API Keys", content, "keys")

    def page_learning(self):
        learn = self.learning()
        projects = learn.get("projects", [])
        details = learn.get("details", {})

        rows = "".join(f'''<tr>
            <td><b>{p}</b></td>
            <td>{details.get(p,{}).get("files",0)}</td>
            <td>{details.get(p,{}).get("functions",0)}</td>
        </tr>''' for p in projects)

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{learn.get("projects_learned",0)}</div><div class="label">Projects</div></div>
            <div class="stat-box"><div class="value">{learn.get("total_functions",0)}</div><div class="label">Functions</div></div>
            <div class="stat-box"><div class="value">{learn.get("total_classes",0)}</div><div class="label">Classes</div></div>
        </div>
        <div class="section">
            <p style="color:#666;margin-bottom:15px;">Last updated: {learn.get("last_updated","never")[:19]}</p>
            <table>
                <tr><th>Project</th><th>Files</th><th>Functions</th></tr>
                {rows}
            </table>
        </div>'''
        return self.base_html("Learning", content, "learning")

    def page_errors(self):
        errs = self.errors()

        rows = "".join(f'''<div class="card warn">
            <small style="color:#fa0">{e.get("source","")}</small><br>
            {e.get("message","")[:200]}
        </div>''' for e in errs) or '<p style="color:#0f8">No recent errors!</p>'

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value" style="color:{"#f44" if errs else "#0f8"}">{len(errs)}</div><div class="label">Recent Errors</div></div>
        </div>
        <div class="section">{rows}</div>'''
        return self.base_html("Errors", content, "errors")

    def page_rising(self):
        repos = self.rising()

        rows = "".join(f'''<tr>
            <td><a href="{r["url"]}" style="color:#0af" target="_blank"><b>{r["name"]}</b></a></td>
            <td>{r["stars"]} ⭐</td>
            <td style="color:#0f8">+{r["growth"]}/day</td>
        </tr>''' for r in repos)

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{len(repos)}</div><div class="label">Tracked Repos</div></div>
        </div>
        <div class="section">
            <table>
                <tr><th>Repository</th><th>Stars</th><th>Growth</th></tr>
                {rows}
            </table>
        </div>'''
        return self.base_html("Rising Stars", content, "rising")

    def page_alerts(self):
        alerts = self.alerts()

        rows = "".join(f'''<div class="card {"error" if a.get("priority")=="high" else "warn"}">
            <b>{a.get("title","")}</b><br>
            <small>{a.get("message","")[:200]}</small><br>
            <a href="{a.get("url","")}" style="color:#0af" target="_blank">{a.get("url","")[:50]}</a>
        </div>''' for a in alerts) or '<p style="color:#0f8">No alerts!</p>'

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{len(alerts)}</div><div class="label">Total Alerts</div></div>
        </div>
        <div class="section">{rows}</div>'''
        return self.base_html("Alerts", content, "alerts")

    def dashboard(self):
        s = self.stats()
        sys = self.system_stats()
        svcs = self.services()
        keys = self.api_keys()
        learn = self.learning()
        errs = self.errors()[:3]
        mem = sys.get("memory", {})

        online_svcs = sum(1 for svc in svcs if svc.get("status") == "online")

        content = f'''
        <div class="stats-row">
            <div class="stat-box"><div class="value">{online_svcs}/{len(svcs)}</div><div class="label">Services Online</div></div>
            <div class="stat-box"><div class="value">{mem.get("percent",0)}%</div><div class="label">Memory</div></div>
            <div class="stat-box"><div class="value">{len(keys)}</div><div class="label">API Keys</div></div>
            <div class="stat-box"><div class="value">{learn.get("projects_learned",0)}</div><div class="label">Projects Learned</div></div>
            <div class="stat-box"><div class="value" style="color:{"#f44" if errs else "#0f8"}">{len(errs)}</div><div class="label">Errors</div></div>
        </div>

        <div class="grid">
            <div class="section">
                <h3 style="color:#0af;margin-bottom:10px;">💾 Quick System</h3>
                <div class="card">Memory: {mem.get("used_mb",0)}MB / {mem.get("total_mb",0)}MB
                <div class="meter"><div class="meter-fill" style="width:{mem.get("percent",0)}%;background:#0f8;"></div></div></div>
                <div class="card">Uptime: {sys.get("uptime","?")}</div>
            </div>

            <div class="section">
                <h3 style="color:#0af;margin-bottom:10px;">🤖 Services</h3>
                {"".join(f'<div class="card {"online" if svc.get("status")=="online" else "offline"}"><span class="dot {"green" if svc.get("status")=="online" else "red"}"></span>{svc["name"]}</div>' for svc in svcs[:5])}
                <a href="/services" style="color:#0af;font-size:0.9em;">View all {len(svcs)} →</a>
            </div>

            <div class="section">
                <h3 style="color:#0af;margin-bottom:10px;">🔑 API Keys</h3>
                {"".join(f'<div class="card {"ok" if k.get("status")=="ok" else "error"}"><b>{k.get("service","")}</b>: {k.get("active","")}</div>' for k in keys)}
            </div>

            <div class="section">
                <h3 style="color:#0af;margin-bottom:10px;">❌ Recent Errors</h3>
                {"".join(f'<div class="card warn"><small>{e.get("source","")}</small><br>{e.get("message","")[:80]}</div>' for e in errs) or '<p style="color:#0f8">No errors!</p>'}
                <a href="/errors" style="color:#0af;font-size:0.9em;">View all →</a>
            </div>
        </div>'''
        return self.base_html("Dashboard", content, "dashboard")

    def log_message(self, *a): pass

if __name__ == "__main__":
    print("Starting AGI Dashboard v3 on :3457")
    HTTPServer(('0.0.0.0', 3457), H).serve_forever()
