import os, json, shutil, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ["AGENT_TOKEN"]

def meminfo():
    m = {}
    for l in open("/host/proc/meminfo"):
        k, v = l.split(":"); m[k] = int(v.split()[0])
    total = m["MemTotal"] // 1024
    avail = m["MemAvailable"] // 1024
    return total, total - avail

def containers():
    try:
        out = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=5).stdout
        return len(out.split())
    except Exception:
        return None

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics" or self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        rt, ru = meminfo()
        d = shutil.disk_usage("/host/data")
        load = float(open("/host/proc/loadavg").read().split()[0])
        body = json.dumps({
            "ram_total_mb": rt, "ram_used_mb": ru,
            "disk_total_gb": d.total // 2**30, "disk_used_gb": d.used // 2**30,
            "load_1m": load, "containers_running": containers(),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

HTTPServer(("0.0.0.0", 8080), H).serve_forever()
