import os, json, shutil, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ["AGENT_TOKEN"]
HOST = os.environ.get("HOST_ROOT", "/host")

def meminfo():
    m = {}
    for l in open(f"{HOST}/proc/meminfo"):
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

def partitions():
    res, seen = [], set()
    for l in open("/proc/self/mounts"):
        p = l.split()
        if len(p) < 3:
            continue
        dev, mount, fstype = p[0], p[1], p[2]
        if mount != HOST and not mount.startswith(HOST + "/"):
            continue
        if fstype not in ("ext4", "xfs", "btrfs", "zfs") or not dev.startswith("/dev/"):
            continue
        host_mount = mount[len(HOST):] or "/"
        if host_mount in seen or host_mount.startswith(("/var/lib/docker", "/data/docker", "/snap", "/boot")):
            continue
        seen.add(host_mount)
        try:
            u = shutil.disk_usage(mount)
        except OSError:
            continue
        res.append({
            "mount": host_mount,
            "total_gb": round(u.total / 2**30, 1),
            "used_gb": round(u.used / 2**30, 1),
            "percent": round(u.used * 100 / u.total, 1),
        })
    return res

def main_disk():
    # /data si elle existe comme partition dédiée (srv1), sinon la racine
    for path in (f"{HOST}/data", HOST):
        try:
            return shutil.disk_usage(path)
        except OSError:
            continue

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/metrics" or self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        rt, ru = meminfo()
        d = main_disk()
        load = float(open(f"{HOST}/proc/loadavg").read().split()[0])
        body = json.dumps({
            "ram_total_mb": rt, "ram_used_mb": ru,
            "disk_total_gb": d.total // 2**30, "disk_used_gb": d.used // 2**30,
            "load_1m": load, "containers_running": containers(),
            "partitions": partitions(),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

HTTPServer(("0.0.0.0", 8080), H).serve_forever()
