#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Портфолио админ-панелі
-----------------------
Бір файлды қолданба (тек стандартты кітапханалар):
  - Сайтты өзі қызмет етеді (portfolio/ қапшығын)
  - /admin — админ интерфейсі (парольмен қорғалған)
  - /admin/api/* — мәтінді өзгерту, видео жүктеу/өшіру/орын ауыстыру,
    GitHub-қа жариялау, аналитика
  - /api/track/* — сайттан келетін кіру/ойнау оқиғаларын қабылдайды
  - Туннельді өзі басқарады (cloudflared) — phone-нан сайтқа кіру үшін

Іске қосу:  python3 admin.py   (немесе  python3 admin.py start)
Ашу:        http://127.0.0.1:8138/admin
"""

import base64
import hashlib
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))          # admin/ қапшығы
SITE = os.path.dirname(BASE)                                # portfolio/ қапшығы
DATA_FILE = os.path.join(BASE, "admin_data.json")
LOG_FILE = os.path.join(BASE, "analytics_log.json")
CONF_FILE = os.path.join(BASE, "admin_config.json")
PORT = 8138
REPO = "nuuurzat/miras-portfolio"
PAGES_URL = "https://nuuurzat.github.io/miras-portfolio/"
DEFAULT_PASSWORD = "miras1234"
LOCK = threading.Lock()
TUNNEL = {"proc": None, "url": "", "status": "off"}
GH_CACHE = {"t": 0, "data": None}

# ---------------------------------------------------------------
# Көмекшілер
# ---------------------------------------------------------------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    return load_json(DATA_FILE, {})

def save_data(d):
    save_json(DATA_FILE, d)

def load_log():
    return load_json(LOG_FILE, {"views": [], "plays": []})

def save_log(l):
    with LOCK:
        l["views"] = l["views"][-5000:]
        l["plays"] = l["plays"][-5000:]
        save_json(LOG_FILE, l)

def get_conf():
    c = load_json(CONF_FILE, None)
    if not c:
        salt = secrets.token_hex(8)
        c = {"salt": salt, "hash": hashlib.sha256((DEFAULT_PASSWORD + salt).encode()).hexdigest()}
        save_json(CONF_FILE, c)
    return c

def check_password(pw):
    c = get_conf()
    return hashlib.sha256((pw + c["salt"]).encode()).hexdigest() == c["hash"]

def set_password(pw):
    salt = secrets.token_hex(8)
    c = {"salt": salt, "hash": hashlib.sha256((pw + salt).encode()).hexdigest()}
    save_json(CONF_FILE, c)

# Админ сессиялары
SESSIONS = {}
LOGIN_ATTEMPTS = {}

def make_session():
    t = secrets.token_hex(24)
    SESSIONS[t] = time.time() + 24 * 3600
    return t

def check_session(cookie):
    t = cookie
    exp = SESSIONS.get(t)
    if exp and exp > time.time():
        return True
    SESSIONS.pop(t, None)
    return False

# ---------------------------------------------------------------
# Трек оқиғалары
# ---------------------------------------------------------------
def track_event(kind, params, ip):
    log = load_log()
    entry = {"t": int(time.time()), "ip": ip}
    if kind == "view":
        entry.update({"vid": params.get("vid", "")[:40], "path": params.get("path", "")[:120]})
        log["views"].append(entry)
    else:
        entry["v"] = params.get("v", "")[:160]
        log["plays"].append(entry)
    save_log(log)

def stats_track(period=14):
    log = load_log()
    now = time.time()
    cut = now - period * 86400
    views = [v for v in log["views"] if v["t"] >= cut]
    plays = [p for p in log["plays"] if p["t"] >= cut]
    uniq_days = {}
    for v in views:
        day = time.strftime("%Y-%m-%d", time.localtime(v["t"]))
        uniq_days.setdefault(day, set()).add(v["vid"])
    by_file = {}
    for p in plays:
        by_file[p["v"]] = by_file.get(p["v"], 0) + 1
    recent = sorted(log["plays"], key=lambda x: -x["t"])[:10]
    recent_v = sorted(log["views"], key=lambda x: -x["t"])[:10]
    return {
        "visits_total": len(views),
        "visits_unique": len({v["vid"] for v in views if v["vid"]}),
        "plays_total": len(plays),
        "plays_by_file": sorted(by_file.items(), key=lambda kv: -kv[1]),
        "recent_plays": recent,
        "recent_views": recent_v,
        "days": len(uniq_days),
    }

# ---------------------------------------------------------------
# GitHub трафигі (analytics)
# ---------------------------------------------------------------
def gh_traffic():
    if GH_CACHE["data"] and time.time() - GH_CACHE["t"] < 600:
        return GH_CACHE["data"]
    try:
        out = subprocess.run(
            ["gh", "api", "repos/%s/traffic/views" % REPO],
            capture_output=True, text=True, timeout=30)
        v = json.loads(out.stdout)
        out2 = subprocess.run(
            ["gh", "api", "repos/%s/traffic/clones" % REPO],
            capture_output=True, text=True, timeout=30)
        c = json.loads(out2.stdout)
        data = {"views": v.get("count", 0), "unique": v.get("uniques", 0),
                "daily_views": v.get("views", []),
                "clones": c.get("count", 0), "daily_clones": c.get("clones", [])}
        GH_CACHE.update(t=time.time(), data=data)
        return data
    except Exception as e:
        return {"error": str(e), "views": 0, "unique": 0, "daily_views": [], "clones": 0, "daily_clones": []}

# ---------------------------------------------------------------
# content.js генерациясы
# ---------------------------------------------------------------
def gen_content_js(d):
    langs = {}
    for code, L in d["langs"].items():
        langs[code] = {"ui": L["ui"], "meta": L["meta"], "cases": [], "services": L["services"], "stats": L["stats"]}
    files = d["case_files"]
    files_js = ",\n".join(
        '  { src: %r, poster: %r }' % (f["src"], f.get("poster", "")) for f in files)
    track = d.get("track_api", "")
    js = """/* ============================================================
   САЙТ КОНТЕНТІ — бұл файлды АДМИН-ПАНЕЛЬ автоматты жасайды.
   Қолмен өзгертпеңіз: portfolio/admin/ сайтындағы админ-панельден
   өзгертіңіз (http://127.0.0.1:8138/admin).
   ============================================================ */

const CASE_FILES = [
%s
];

window.PORTFOLIO_DATA = %s;
window.PORTFOLIO_DATA.trackApi = %r;

(function () {
  const D = window.PORTFOLIO_DATA;
  const titleOf = (src) =>
    src.split("/").pop().replace(/\\.(mp4|mov|webm)$/i, "").trim();
  for (const lang in D.languages) {
    D.languages[lang].cases = CASE_FILES.map((f) => ({
      title: titleOf(f.src),
      tags: [],
      year: "",
      media: [{ type: "video", src: f.src, poster: f.poster || "" }]
    }));
  }
})();
""" % (files_js, json.dumps({"defaultLang": "kk", "contacts": d["contact"],
                            "companies": d["companies"], "languages": langs},
                           ensure_ascii=False, indent=2), track)
    with open(os.path.join(SITE, "js", "content.js"), "w", encoding="utf-8") as f:
        f.write(js)

# ---------------------------------------------------------------
# GitHub-қа жариялау
# ---------------------------------------------------------------
def git_cmd(args, timeout=900):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env, cwd=SITE)

def publish():
    if not os.path.isdir(os.path.join(SITE, ".git")):
        return {"ok": False, "msg": ".git табылмады"}
    st = git_cmd(["git", "status", "--porcelain"]).stdout.strip()
    if not st:
        return {"ok": True, "changed": False, "msg": "Өзгеріс жоқ — сайт ескісіндей"}
    git_cmd(["git", "config", "user.name", "nuuurzat"])
    git_cmd(["git", "config", "user.email", "nuuurzat@users.noreply.github.com"])
    git_cmd(["git", "add", "-A"])
    git_cmd(["git", "commit", "-m", "admin: сайт жаңартылды"])
    try:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=30).stdout.strip()
        auth = "basic " + base64.b64encode(("x-access-token:" + token).encode()).decode()
        r = git_cmd(["git", "-c", "http.extraHeader=Authorization: %s" % auth, "push", "origin", "main"])
        if r.returncode != 0:
            return {"ok": False, "changed": True, "msg": (r.stderr or r.stdout)[-400:]}
        return {"ok": True, "changed": True, "msg": "Жарияланды ✓"}
    except Exception as e:
        return {"ok": False, "changed": True, "msg": str(e)}

# ---------------------------------------------------------------
# Туннель (cloudflared)
# ---------------------------------------------------------------
TF_BIN = os.path.join(os.path.dirname(os.path.dirname(BASE)), "tools", "cloudflared")

def tunnel_start():
    global TUNNEL
    if TUNNEL["proc"] and TUNNEL["proc"].poll() is None:
        return {"ok": True, "status": "on", "url": TUNNEL["url"]}
    if not os.path.exists(TF_BIN):
        TUNNEL["status"] = "no-bin"
        return {"ok": False, "status": "no-bin", "msg": "cloudflared табылмады"}
    TUNNEL["status"] = "starting"
    proc = subprocess.Popen(
        [TF_BIN, "tunnel", "--url", "http://127.0.0.1:%d" % PORT, "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    TUNNEL["proc"] = proc

    def reader():
        for line in proc.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if m:
                url = m.group(0)
                if url != TUNNEL["url"]:
                    TUNNEL["url"] = url
                    TUNNEL["status"] = "on"
                    d = load_data()
                    if d.get("track_api") != url:
                        d["track_api"] = url
                        save_data(d)
                        gen_content_js(d)
                        publish()
    threading.Thread(target=reader, daemon=True).start()
    return {"ok": True, "status": "starting", "url": TUNNEL["url"]}

def tunnel_stop():
    global TUNNEL
    if TUNNEL["proc"]:
        TUNNEL["proc"].terminate()
        TUNNEL["proc"] = None
    TUNNEL["url"] = ""
    TUNNEL["status"] = "off"
    d = load_data()
    if d.get("track_api"):
        d["track_api"] = ""
        save_data(d)
        gen_content_js(d)
        publish()
    return {"ok": True, "status": "off"}

# ---------------------------------------------------------------
# Видео операциялары
# ---------------------------------------------------------------
SAFE_RE = re.compile(r"[^\w\s.\-()а-яА-ЯәғқңөұүһіӘҒҚҢӨҰҮҺІ]+")

def sanitize_name(name):
    name = os.path.basename(name)
    name = SAFE_RE.sub("-", name).strip("- ")
    return name or "video.mp4"

def make_poster(video_path, folder):
    poster_dir = os.path.join(SITE, "img", "posters", folder)
    os.makedirs(poster_dir, exist_ok=True)
    try:
        subprocess.run(["qlmanage", "-t", "-s", "480", "-o", poster_dir, video_path],
                       capture_output=True, text=True, timeout=30)
    except Exception:
        pass
    out = os.path.join(poster_dir, os.path.basename(video_path) + ".png")
    if os.path.exists(out):
        return "posters/%s/%s.png" % (folder, os.path.basename(video_path)) if folder else "posters/%s.png" % os.path.basename(video_path)
    return ""

def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    for i in range(2, 100):
        cand = "%s-%d%s" % (base, i, ext)
        if not os.path.exists(cand):
            return cand
    return path

def delete_video(src):
    d = load_data()
    keep = [f for f in d["case_files"] if f["src"] != src]
    if len(keep) == len(d["case_files"]):
        return {"ok": False, "msg": "Табылмады"}
    removed = [f for f in d["case_files"] if f["src"] == src]
    d["case_files"] = keep
    save_data(d)
    gen_content_js(d)
    for f in removed:
        for key in ("src", "poster"):
            p = os.path.join(SITE, "img", f.get(key, ""))
            if f.get(key) and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
    return {"ok": True}

def move_video(src, direction):
    d = load_data()
    files = d["case_files"]
    idx = next((i for i, f in enumerate(files) if f["src"] == src), None)
    if idx is None:
        return {"ok": False, "msg": "Табылмады"}
    j = idx - 1 if direction == "up" else idx + 1
    if j < 0 or j >= len(files):
        return {"ok": True}
    files[idx], files[j] = files[j], files[idx]
    save_data(d)
    gen_content_js(d)
    return {"ok": True}

# ---------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------
class H(BaseHTTPRequestHandler):
    server_version = "Admin/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    # --- helpers ---
    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def read_body(self, limit=256 * 1024 * 1024):
        ln = int(self.headers.get("Content-Length") or 0)
        if ln > limit:
            return b""
        return self.rfile.read(ln)

    def client_ip(self):
        return self.client_address[0] or "?"

    def is_admin_authed(self):
        ck = self.headers.get("Cookie") or ""
        m = re.search(r"adm=([0-9a-f]+)", ck)
        return bool(m and check_session(m.group(1)))

    # --- GET ---
    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def do_OPTIONS(self):
        self.send(204, b"")

    def route(self):
        p = urllib.parse.urlparse(self.path)
        path = p.path
        q = urllib.parse.parse_qs(p.query)
        try:
            if path == "/admin" or path == "/admin/":
                return self.send(200, ADMIN_HTML, "text/html; charset=utf-8")
            if path.startswith("/admin/api/"):
                return self.admin_api(path, q)
            if path.startswith("/api/track/"):
                return self.api_track(path, q)
            if path.startswith("/admin"):
                return self.send(404, {"ok": False})
            return self.static(path)
        except BrokenPipeError:
            pass
        except Exception as e:
            self.send(500, {"ok": False, "msg": repr(e)})

    # --- статикалық файлдар (сайт) ---
    def static(self, path):
        path = urllib.parse.unquote(path)
        if path == "/":
            path = "/index.html"
        fp = os.path.normpath(os.path.join(SITE, path.lstrip("/")))
        if not fp.startswith(os.path.normpath(SITE)) or not os.path.isfile(fp):
            return self.send(404, "not found", "text/plain")
        ctype, _ = mimetypes.guess_type(fp)
        ctype = ctype or "application/octet-stream"
        if ctype == "text/javascript":
            ctype = "application/javascript"
        rng = self.headers.get("Range")
        size = os.path.getsize(fp)
        with open(fp, "rb") as f:
            if rng and rng.startswith("bytes="):
                try:
                    start, end = rng[6:].split("-")
                    start = int(start or 0)
                    end = int(end) if end else size - 1
                    end = min(end, size - 1)
                    f.seek(start)
                    data = f.read(end - start + 1)
                    self.send_response(206)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception:
                    pass
            data = f.read()
        self.send(200, data, ctype)

    # --- трекинг ---
    def api_track(self, path, q):
        one = lambda k, d="": (q.get(k) or [d])[0]
        if path.endswith("/view"):
            track_event("view", {"vid": one("vid"), "path": one("path")}, self.client_ip())
        elif path.endswith("/play"):
            track_event("play", {"v": one("v")}, self.client_ip())
        return self.send(200, {"ok": True})

    # --- админ API ---
    def admin_api(self, path, q):
        # login — пароль талап етілмейді
        if path.endswith("/login"):
            body = json.loads(self.read_body(limit=1024 * 1024) or b"{}")
            ip = self.client_ip()
            now = time.time()
            attempts = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
            LOGIN_ATTEMPTS[ip] = attempts
            if len(attempts) >= 6:
                return self.send(429, {"ok": False, "msg": "Тым көп әрекет — 1 минут күтіңіз"})
            if not check_password(body.get("password", "")):
                attempts.append(now)
                return self.send(401, {"ok": False, "msg": "Пароль қате"})
            tok = make_session()
            return self.send(200, {"ok": True, "token": tok},
                             extra={"Set-Cookie": "adm=%s; Path=/; SameSite=Lax" % tok})
        if not self.is_admin_authed():
            return self.send(401, {"ok": False, "msg": "Кіру қажет"})
        if path.endswith("/me"):
            return self.send(200, {"ok": True})
        if path.endswith("/state"):
            d = load_data()
            return self.send(200, {"ok": True, "data": d, "pages": PAGES_URL})
        if path.endswith("/save_text"):
            body = json.loads(self.read_body() or b"{}")
            d = load_data()
            if isinstance(body.get("langs"), dict):
                for code, L in body["langs"].items():
                    if code in d["langs"]:
                        if isinstance(L.get("meta"), dict):
                            d["langs"][code]["meta"].update(L["meta"])
                        if isinstance(L.get("services"), list):
                            d["langs"][code]["services"] = L["services"]
                        if isinstance(L.get("stats"), list):
                            d["langs"][code]["stats"] = L["stats"]
            if isinstance(body.get("contact"), dict):
                d["contact"].update(body["contact"])
            if isinstance(body.get("companies"), list):
                d["companies"] = [{"name": str(c.get("name", ""))[:120],
                                   "href": str(c.get("href", ""))[:240]} for c in body["companies"] if c.get("name")]
            save_data(d)
            gen_content_js(d)
            r = publish()
            return self.send(200, {"ok": True, "publish": r})
        if path.endswith("/videos"):
            d = load_data()
            log = load_log()
            counts = {}
            for p in log["plays"]:
                counts[p["v"]] = counts.get(p["v"], 0) + 1
            files = [{"src": f["src"], "poster": f.get("poster", ""),
                      "plays": counts.get(f["src"], 0)} for f in d["case_files"]]
            return self.send(200, {"ok": True, "videos": files})
        if path.endswith("/video/delete"):
            body = json.loads(self.read_body(limit=1 * 1024 * 1024) or b"{}")
            delete_video(body.get("src", ""))
            r = publish()
            return self.send(200, {"ok": True, "publish": r})
        if path.endswith("/video/move"):
            body = json.loads(self.read_body(limit=1 * 1024 * 1024) or b"{}")
            move_video(body.get("src", ""), body.get("dir", "down"))
            r = publish()
            return self.send(200, {"ok": True, "publish": r})
        if path.endswith("/publish"):
            r = publish()
            return self.send(200, {"ok": True, "publish": r})
        if path.endswith("/stats"):
            g = gh_traffic()
            t = stats_track()
            d = load_data()
            return self.send(200, {"ok": True, "gh": g, "track": t,
                                   "tunnel": TUNNEL, "check": self.tunnel_check()})
        if path.endswith("/tunnel/restart"):
            return self.send(200, tunnel_start())
        if path.endswith("/tunnel/stop"):
            return self.send(200, tunnel_stop())
        if path.endswith("/password"):
            body = json.loads(self.read_body(limit=1 * 1024 * 1024) or b"{}")
            if not check_password(body.get("current", "")):
                return self.send(401, {"ok": False, "msg": "Ағымдағы пароль қате"})
            new = body.get("new", "")
            if len(new) < 6:
                return self.send(400, {"ok": False, "msg": "Пароль кемінде 6 таңба"})
            set_password(new)
            return self.send(200, {"ok": True})
        if path.endswith("/video/upload"):
            return self.upload_api()
        return self.send(404, {"ok": False})

    def tunnel_check(self):
        try:
            import urllib.request
            r = urllib.request.urlopen("http://127.0.0.1:%d/admin/api/me" % PORT, timeout=3)
            return r.status == 401 or r.status == 200
        except Exception:
            return False

    def upload_api(self):
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=(.+)", ctype)
        if not m:
            return self.send(400, {"ok": False, "msg": "boundary жоқ"})
        boundary = m.group(1).strip('"').encode()
        body = self.read_body(limit=2 * 1024 * 1024 * 1024)
        d = load_data()
        added = []
        created = []
        try:
            for part in body.split(b"--" + boundary):
                if b"Content-Disposition" not in part:
                    continue
                head, _, content = part.partition(b"\r\n\r\n")
                content = content.rstrip(b"\r\n")
                fn = None
                for line in head.split(b"\r\n"):
                    if b"filename=" in line:
                        fn = line.split(b'filename="')[1].split(b'"')[0].decode("utf-8", "replace")
                if not fn or not content:
                    continue
                fn = sanitize_name(fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".mp4", ".mov", ".webm"):
                    return self.send(400, {"ok": False, "msg": "Тек MP4/MOV/WebM: %s" % fn})
                # MOV → MP4 (егер ffmpeg болса)
                tmp = os.path.join(SITE, "img", unique_path(fn))
                with open(tmp, "wb") as f:
                    f.write(content)
                final = tmp
                if ext == ".mov":
                    try:
                        import imageio_ffmpeg
                        ff = imageio_ffmpeg.get_ffmpeg_exe()
                        mp4 = os.path.splitext(tmp)[0] + ".mp4"
                        r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", tmp,
                                            "-c:v", "libx264", "-crf", "26", "-preset", "veryfast",
                                            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", mp4],
                                           capture_output=True, timeout=1800)
                        if r.returncode == 0 and os.path.getsize(mp4) > 1000:
                            os.remove(tmp)
                            final = mp4
                            fn = os.path.basename(mp4)
                    except Exception:
                        pass
                rel = os.path.relpath(final, os.path.join(SITE, "img"))
                created.append(final)
                folder = os.path.dirname(rel)
                poster = make_poster(final, folder)
                entry = {"src": rel, "poster": poster}
                d["case_files"].append(entry)
                added.append(rel)
        except Exception as e:
                for f in created:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                return self.send(500, {"ok": False, "msg": str(e)[:200]})
        save_data(d)
        gen_content_js(d)
        r = publish()
        return self.send(200, {"ok": True, "added": added, "publish": r})
ADMIN_HTML = """<!doctype html><html lang="kk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Админ — портфолио</title>
<style>
:root{--bg:#F4F1EA;--card:#fff;--ink:#17150F;--soft:#6E6857;--line:#E4DFD3;--acc:#C7F231;--accink:#141406;--red:#E5533D;--green:#2FA36B;--blue:#3D7BE5}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,'Inter',system-ui,sans-serif;padding:20px;max-width:1060px;margin:0 auto}
h1{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:22px;margin-bottom:18px}
h1 small{color:var(--soft);font-weight:400;font-size:13px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:22px}
.tab{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:9px 20px;cursor:pointer;font-size:14px;font-weight:600;color:var(--soft)}
.tab.on{background:var(--ink);color:var(--bg)}
.panel{display:none}.panel.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:16px}
.card h3{font-size:15px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:10px}
.stat{background:var(--bg);border-radius:12px;padding:14px}
.stat b{display:block;font-size:24px}
.stat span{font-size:12px;color:var(--soft)}
label{display:block;font-size:12.5px;color:var(--soft);margin:10px 0 4px}
input,textarea{width:100%;border:1px solid var(--line);border-radius:10px;padding:10px 12px;font:14px inherit;background:#fff;color:var(--ink)}
textarea{min-height:88px;resize:vertical}
.btn{display:inline-block;border:none;border-radius:999px;padding:11px 24px;font-size:14px;font-weight:600;cursor:pointer;background:var(--ink);color:var(--bg)}
.btn.acc{background:var(--acc);color:var(--accink)}
.btn.ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
.btn.red{background:var(--red);color:#fff}
.btn.sm{padding:6px 14px;font-size:12.5px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.spacer{flex:1}
.vlist{display:flex;flex-direction:column;gap:8px}
.vitem{display:flex;align-items:center;gap:12px;background:var(--bg);border-radius:12px;padding:8px 12px}
.vitem img{width:44px;height:64px;object-fit:cover;border-radius:8px;background:#222}
.vitem .name{flex:1;font-size:13.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vitem .plays{font-size:12px;color:var(--soft)}
.drop{border:2px dashed var(--line);border-radius:16px;padding:34px;text-align:center;color:var(--soft);cursor:pointer;transition:.2s;background:var(--card)}
.drop.over{border-color:var(--acc);background:#fafce8}
#toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:12px 22px;border-radius:999px;font-size:14px;opacity:0;transition:.3s;z-index:99;max-width:90vw}
#toast.on{opacity:1}
.bars{display:flex;align-items:flex-end;gap:6px;height:90px;margin:12px 0}
.bar{flex:1;background:var(--acc);border-radius:4px 4px 0 0;min-height:2px;position:relative}
.bar span{position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);font-size:10px;color:var(--soft)}
.login{max-width:380px;margin:12vh auto;background:#fff;border:1px solid var(--line);border-radius:18px;padding:30px}
.login h2{margin-bottom:16px;font-size:18px}
.note{font-size:12.5px;color:var(--soft);margin-top:10px}
.ok{color:var(--green);font-weight:600}.err{color:var(--red);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
.thin{font-size:12px;color:var(--soft)}
</style></head><body>
<div id="loginBox" class="login" style="display:none">
 <h2>🔐 Админге кіру</h2>
 <input id="pw" type="password" placeholder="Пароль" onkeydown="if(event.key=='Enter')doLogin()">
 <div style="margin-top:14px"><button class="btn" onclick="doLogin()">Кіру</button></div>
 <div id="lmsg" class="err" style="margin-top:10px"></div>
</div>

<div id="app" style="display:none">
<h1>🎛️ Портфолио админ-панелі <small id="pg"></small></h1>
<div class="tabs">
 <div class="tab on" data-t="stats">📊 Аналитика</div>
 <div class="tab" data-t="text">✏️ Мәтіндер</div>
 <div class="tab" data-t="videos">🎬 Видеолар</div>
 <div class="tab" data-t="settings">⚙️ Баптаулар</div>
</div>

<div class="panel on" id="p-stats">
 <div class="card"><h3>👥 GitHub Pages трафигі</h3>
  <div class="grid">
   <div class="stat"><b id="ghv">–</b><span>Кіру (14 күн)</span></div>
   <div class="stat"><b id="ghu">–</b><span>Бірегей келушілер</span></div>
   <div class="stat"><b id="ghc">–</b><span>Клондар</span></div>
  </div>
  <div class="bars" id="ghbars"></div>
  <p class="note">GitHub-тың ресми трафик есебі — сенімді дереккөз.</p>
 </div>
 <div class="card"><h3>🎥 Видео ойнаулар (туннель арқылы)</h3>
  <div class="grid">
   <div class="stat"><b id="pv_t">–</b><span>Ашу саны</span></div>
   <div class="stat"><b id="pv_u">–</b><span>Сайтқа кірулер</span></div>
   <div class="stat"><b id="pv_d">–</b><span>Бірегей келушілер</span></div>
  </div>
  <table><thead><tr><th>Видео</th><th>Ойнаулар</th></tr></thead><tbody id="pv_list"></tbody></table>
  <p class="note">Соңғы 14 күнде түннель жұмыс істеп тұрғанда ғана жазылады (қалған уақытта GitHub трафигі жеткілікті).</p>
 </div>
 <div class="card"><h3>🕐 Соңғы оқиғалар</h3>
  <table><thead><tr><th>Уақыт</th><th>Тип</th><th>Дерек</th></tr></thead><tbody id="ev_list"></tbody></table>
 </div>
</div>

<div class="panel" id="p-text">
 <div class="card"><h3>🌐 Негізгі мәтіндер (3 тіл)</h3>
  <div id="langs"></div>
  <div class="row" style="margin-top:14px"><button class="btn acc" onclick="saveText()">💾 Сақтау және сайтқа шығару</button><span id="tsave" class="thin"></span></div>
 </div>
 <div class="card"><h3>📱 Байланыс</h3>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">
   <div><label>Телефон (көрінетін)</label><input id="ct_phone"></div>
   <div><label>Телефон (tel: үшін)</label><input id="ct_phoneHref"></div>
   <div><label>Telegram хэндл</label><input id="ct_tg"></div>
   <div><label>Telegram сілтеме</label><input id="ct_tghref"></div>
   <div><label>Instagram хэндл</label><input id="ct_insta"></div>
   <div><label>Instagram сілтеме</label><input id="ct_instahref"></div>
  </div>
 </div>
 <div class="card"><h3>🤝 Компаниялар (бір жол: Атау | сілтеме)</h3>
  <textarea id="ct_companies" rows="11"></textarea>
 </div>
</div>

<div class="panel" id="p-videos">
 <div class="card">
  <h3>⬆️ Жаңа видео жүктеу MP4</h3>
  <div class="drop" id="drop">Файлдарды осы жерге тастаңыз немесе басып таңдаңыз<br><span class="thin">MP4 — бірден бірнеше файл тастауға болады. Автоматты постер жасалады.</span></div>
  <input type="file" id="file" multiple accept=".mp4,.mov,.webm" style="display:none">
  <div id="upmsg" style="margin-top:10px"></div>
 </div>
 <div class="card"><h3>🎬 Видеолар тізімі (ретін өзгерту, өшіру)</h3>
  <div class="vlist" id="vlist"></div>
 </div>
 <div class="card"><div class="row"><button class="btn acc" onclick="publish()">🚀 Сайтты жаңарту (GitHub)</button><span id="pmsg" class="thin"></span><span class="spacer"></span><a class="btn ghost sm" id="siteLink" href="#" target="_blank">Сайтты ашу ↗</a></div></div>
</div>

<div class="panel" id="p-settings">
 <div class="card"><h3>🔐 Парольді өзгерту</h3>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">
   <div><label>Ағымдағы пароль</label><input id="pw_cur" type="password"></div>
   <div><label>Жаңа пароль (мин 6 таңба)</label><input id="pw_new" type="password"></div>
  </div>
  <div class="row" style="margin-top:12px"><button class="btn" onclick="savePw()">Ауыстыру</button><span id="pwmsg" class="thin"></span></div>
 </div>
 <div class="card"><h3>🌍 Туннель (телефоннан кіру)</h3>
  <div class="row"><span id="tstate">–</span><span class="spacer"></span>
   <button class="btn ghost sm" onclick="tunnel('restart')">Қосу</button>
   <button class="btn ghost sm" onclick="tunnel('stop')">Өшіру</button>
  </div>
  <p class="note">Туннель қосылғанда: (1) видео ойнау есебі жазылады, (2) сырттан уақытша сілтеме алынады. Негізгі сілтеме — GitHub Pages, ол туннельсіз де жұмыс істейді. Админ-панельге де туннельден кіруге болады — пароль қажет!</p>
 </div>
 <div class="card"><h3>ℹ️ Ақпарат</h3>
  <p class="note">Сайт: <code id="pg2"></code><br>Админ: <code>http://127.0.0.1:8138/admin</code><br>Түзетулер «Сақтау» басылғанда автоматты GitHub-қа жарияланады.</p>
 </div>
</div>
</div>
<div id="toast"></div>
<script>
const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);
let DATA=null, TOK='';
function toast(m, ok){const t=$('#toast');t.textContent=m;t.style.background=ok?'#17150F':'#E5533D';t.classList.add('on');setTimeout(()=>t.classList.remove('on'),3200)}
function api(path, opts){opts=opts||{};opts.headers=opts.headers||{};if(!opts.method)opts.method='GET';return fetch('/admin/api/'+path,opts).then(async r=>{const j=await r.json().catch(()=>({}));if(r.status===401){showLogin();throw new Error('auth')}return j})}
function showLogin(){$('#app').style.display='none';$('#loginBox').style.display='block';$('#pw').focus()}
function doLogin(){const pw=$('#pw').value;fetch('/admin/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw})}).then(r=>r.json()).then(j=>{if(j.ok){start(j.token)}else{$('#lmsg').textContent=j.msg||'Пароль қате'}})}
function start(tok){TOK=tok;$('#loginBox').style.display='none';$('#app').style.display='block';api('state').then(j=>{if(!j.ok)return;DATA=j.data;$('#pg').textContent=j.pages;$('#pg2').textContent=j.pages;$('#siteLink').href=j.pages;fillText();fillContact();fillCompanies()});loadVideos();loadStats()}
async function isAuth(){try{const j=await api('me');return j.ok}catch(e){return false}}
(function(){isAuth().then(ok=>{if(ok)start('x');else showLogin()})})();
$$('.tab').forEach(t=>t.addEventListener('click',()=>{$$('.tab').forEach(x=>x.classList.remove('on'));$$('.panel').forEach(x=>x.classList.remove('on'));t.classList.add('on');$('#p-'+t.dataset.t).classList.add('on');if(t.dataset.t==='stats')loadStats();if(t.dataset.t==='videos')loadVideos()}));

/* ---- мәтін ---- */
function fillText(){const langs=['kk','ru','en'];const L=['Қазақша','Орысша','Ағылшынша'];let h='';langs.forEach((c,i)=>{const m=DATA.langs[c].meta;h+=`<div style="margin-bottom:18px"><b>${L[i]}</b>
 <label>Аты-жөні</label><input data-lang="${c}" data-f="name" value="${esc(m.name)}">
 <label>Мамандық</label><input data-lang="${c}" data-f="role" value="${esc(m.role)}">
 <label>Слоган</label><input data-lang="${c}" data-f="tagline" value="${esc(m.tagline)}">
 <label>Сипаттама</label><textarea data-lang="${c}" data-f="intro">${esc(m.intro)}</textarea></div>`});$('#langs').innerHTML=h}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function fillContact(){const c=DATA.contact;$('#ct_phone').value=c.phone;$('#ct_phoneHref').value=c.phoneHref;$('#ct_tg').value=c.telegram;$('#ct_tghref').value=c.telegramHref;$('#ct_insta').value=c.instagram;$('#ct_instahref').value=c.instagramHref}
function fillCompanies(){$('#ct_companies').value=DATA.companies.map(c=>c.name+' | '+(c.href||'')).join('\\n')}
function saveText(){const meta={};$$('#langs input,#langs textarea').forEach(el=>{meta[el.dataset.lang]=meta[el.dataset.lang]||{};meta[el.dataset.lang][el.dataset.f]=el.value});
 const companies=$('#ct_companies').value.split('\\n').map(l=>{const m=l.split('|');return {name:(m[0]||'').trim(),href:(m[1]||'').trim()}}).filter(c=>c.name);
 const contact={phone:$('#ct_phone').value,phoneHref:$('#ct_phoneHref').value,telegram:$('#ct_tg').value,telegramHref:$('#ct_tghref').value,instagram:$('#ct_insta').value,instagramHref:$('#ct_instahref').value};
 api('save_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({langs:{kk:{meta:meta.kk},ru:{meta:meta.ru},en:{meta:meta.en}},contact,companies})}).then(j=>{const m=j.publish&&j.publish.msg||'Сақталды';toast(m,j.publish&&j.publish.ok)})}

/* ---- видео ---- */
function loadVideos(){api('videos').then(j=>{if(!j.ok)return;const v=j.videos;let h='';v.forEach((f,i)=>{const name=f.src.split('/').pop();h+=`<div class="vitem"><img src="/img/${encodeURI(f.poster||'')}" onerror="this.style.opacity=.2"><span class="name">${esc(name)}</span><span class="plays">${f.plays} ▶</span>
  <button class="btn ghost sm" onclick="mv('${esc(f.src)}','up')">↑</button>
  <button class="btn ghost sm" onclick="mv('${esc(f.src)}','down')">↓</button>
  <button class="btn red sm" onclick="del('${esc(f.src)}')">Өшіру</button></div>`});$('#vlist').innerHTML=h||'<p class="note">Видео жоқ</p>'})}
function mv(src,dir){api('video/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({src,dir})}).then(j=>{toast((j.publish&&j.publish.msg)||'Орын ауыстырылды',true);loadVideos()})}
function del(src){if(!confirm('Осы видеоны өшіріп, сайттан алып тастау керек пе?'))return;api('video/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({src})}).then(j=>{toast((j.publish&&j.publish.msg)||'Өшірілді',true);loadVideos()})}
const drop=$('#drop'),fi=$('#file');
drop.addEventListener('click',()=>fi.click());
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over')});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');up(e.dataTransfer.files)});
fi.addEventListener('change',()=>{up(fi.files);fi.value=''});
function up(files){if(!files.length)return;$('#upmsg').innerHTML='<span class="thin">Жүктелуде…</span>';const fd=new FormData();for(const f of files)fd.append('f',f);
 api('video/upload',{method:'POST',body:fd}).then(j=>{const m=(j.publish&&j.publish.msg)||('Қосылды: '+(j.added||[]).join(', '));$('#upmsg').innerHTML='<span class="ok">'+m+'</span>';loadVideos();toast(m,true)}).catch(()=>{$('#upmsg').innerHTML='<span class="err">Қате — қайта көріңіз</span>'})}
function publish(){api('publish').then(j=>{toast((j.publish&&j.publish.msg)||'Жарияланды',true);setTimeout(loadStats,2000)})}

/* ---- статистика ---- */
function loadStats(){api('stats').then(j=>{if(!j.ok)return;const g=j.gh,t=j.track;
 $('#ghv').textContent=g.views;$('#ghu').textContent=g.unique;$('#ghc').textContent=g.clones;
 $('#pv_t').textContent=t.plays_total;$('#pv_u').textContent=t.visits_total;$('#pv_d').textContent=t.visits_unique;
 $('#ghbars').innerHTML=(g.daily_views||[]).slice(-14).map(d=>{const day=d.timestamp.slice(5,10);const h=Math.max(4,Math.round(100*d.count/Math.max(1,...(g.daily_views||[]).map(x=>x.count))));return `<div class="bar" style="height:${h}px" title="${day}: ${d.count}"><span>${day}</span></div>`}).join('')||'<span class="note">Дерек жиналмаған күндер әлі — көмекші деректер күн сайын жаңарады</span>';
 $('#pv_list').innerHTML=t.plays_by_file.slice(0,30).map(([v,n])=>`<tr><td>${esc(v.split('/').pop())}</td><td>${n}</td></tr>`).join('')||'<tr><td colspan="2" class="thin">Әзірге ойнаулар жоқ — туннель қосулы болғанда жазылады</td></tr>';
 let evs=[];(t.recent_plays||[]).forEach(p=>evs.push([new Date(p.t*1000),'▶ Видео',p.v.split('/').pop()]));
 (t.recent_views||[]).forEach(v=>evs.push([new Date(v.t*1000),'👁 Кіру',(v.path||'')+(v.vid?' ('+v.vid.slice(0,6)+')':'')]));
 evs.sort((a,b)=>b[0]-a[0]);$('#ev_list').innerHTML=evs.slice(0,20).map(e=>`<tr><td>${e[0].toLocaleString('kk-KZ')}</td><td>${e[1]}</td><td>${esc(String(e[2]))}</td></tr>`).join('')||'<tr><td colspan="3" class="thin">Оқиға жоқ</td></tr>';
 $('#tstate').textContent = j.tunnel.status==='on' ? ('Туннель қосулы: '+j.tunnel.url) : (j.tunnel.status==='no-bin'?'cloudflared жоқ':'Туннель өшірулі');
 })} 

/* ---- баптаулар ---- */
function savePw(){api('password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current:$('#pw_cur').value,new:$('#pw_new').value})}).then(j=>{toast(j.ok?'Пароль ауыстырылды':(j.msg||'Қате'),!!j.ok)}).catch(()=>toast('Ағымдағы пароль қате',false))}
function tunnel(kind){api('tunnel/'+kind,{method:'POST'}).then(j=>{toast(j.url?('Туннель: '+j.url):'Туннель өшірілді',true);setTimeout(loadStats,3000)}).catch(()=>toast('Қате',false))}
</script></body></html>"""

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    # git base баптауы бар ма тексеру (жариялау үшін)
    if not os.path.isdir(os.path.join(SITE, ".git")):
        print("!!! portfolio/.git табылмады — жариялау жұмыс істемейді")
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print("Админ-панель: http://127.0.0.1:%d/admin" % port)
    print("Сайт:         http://127.0.0.1:%d/" % port)
    print("Пароль:       %s" % DEFAULT_PASSWORD)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
