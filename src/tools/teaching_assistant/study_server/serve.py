#!/usr/bin/env python3
"""serve.py — the study server.

Input is the rendered `html/` output already sitting under each course, plus the
`learning` domain of `personal.db`. Operation is an HTTP server on the loopback
interface that serves those pages and records what the learner opens and marks.
Output is a browsable course list, a lesson page carrying its own progress
controls, and a small JSON API the page calls.

Standard library only, as the renderer is: no dependency, no CDN, no build step.

    python3 serve.py                       # serve, land on the course list
    python3 serve.py --course git_course   # land where that course was left
    python3 serve.py --port 8765
    python3 serve.py --self-check          # start, serve, write, exit non-zero on failure

Routes:

    GET  /                        the course list
    GET  /<course>/               that course's rendered index
    GET  /<course>/resume         redirect to the lesson last opened, else the first
    GET  /<course>/<file>         a file from that course's html/ output
    GET  /api/place[?course=]     where each course was left
    GET  /api/marks?course=&lesson=   what is recorded against one lesson
    POST /api/progress            record or clear one thing the learner did
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_TOOLS / "teaching_assistant" / "html_renderer"))
sys.path.insert(0, str(_TOOLS / "personal_db"))

import render  # noqa: E402  (the renderer owns the courses-root resolution)
import personal_write as store  # noqa: E402  (the learning domain's only writer)

LESSON_FILE = re.compile(r"^(?P<course>.+)_lesson_(?P<number>\d+)\.html$")
TOKEN = re.compile(r"\{\{[A-Z_]+\}\}")
LOCAL_SCRIPT = re.compile(
    r"<script>\s*//[^\n]*\n\s*\(function\(\)\{[^<]*?studied-box.*?</script>",
    re.DOTALL)
INJECTION_MARK = "bristol-study-progress"


# ---------------------------------------------------------------------------
# The courses on disk
# ---------------------------------------------------------------------------

def course_dir(root: str, course: str) -> Path:
    return Path(root) / course / "html"


def lessons(root: str, course: str) -> list[dict]:
    """Every rendered lesson of one course, in number order."""
    hdir = course_dir(root, course)
    if not hdir.is_dir():
        return []
    topics = _topics(root, course)
    out = []
    for f in sorted(hdir.iterdir()):
        m = LESSON_FILE.match(f.name)
        if not m:
            continue
        n = int(m.group("number"))
        out.append({"number": n, "file": f.name,
                    "title": topics.get(n, "Lesson %02d" % n)})
    return sorted(out, key=lambda d: d["number"])


def _topics(root: str, course: str) -> dict[int, str]:
    """Lesson titles from the course's own file manifest, when it has one."""
    manifest = Path(root) / course / "syllabus" / "progress.json"
    try:
        data = json.loads(manifest.read_text())
    except (OSError, ValueError):
        return {}
    return {int(l["number"]): l.get("topic") or "Lesson %02d" % int(l["number"])
            for l in data.get("lessons", []) if "number" in l}


def _title(root: str, course: str) -> str:
    manifest = Path(root) / course / "syllabus" / "progress.json"
    try:
        return json.loads(manifest.read_text()).get("course_title") or course
    except (OSError, ValueError):
        return course.replace("_", " ").title()


def courses(root: str) -> list[dict]:
    """Every course with rendered output, in name order."""
    out = []
    for d in sorted(Path(root).iterdir()):
        if not d.is_dir() or not (d / "html").is_dir():
            continue
        ls = lessons(root, d.name)
        if not ls:
            continue
        out.append({"name": d.name, "title": _title(root, d.name),
                    "lessons": ls,
                    "has_index": (d / "html" / "index.html").is_file()})
    return out


# ---------------------------------------------------------------------------
# The pages
# ---------------------------------------------------------------------------

LIST_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Courses</title>
<style>
body{background:#fbfaf7;color:#1f1c18;font-family:Georgia,serif;
  max-width:740px;margin:0 auto;padding:48px 24px;font-size:18px;line-height:1.6}
h1{font-size:28px;margin-bottom:4px}
.sub{color:#6b6359;font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:13px;margin-top:0}
.course{border-top:1px solid #e4ddd2;padding:20px 0}
.course h2{font-size:21px;margin:0 0 6px}
.place{color:#6b6359;font-size:16px;margin:0 0 10px}
a{color:#7a4b2b}
.go{font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;margin-right:16px}
@media(prefers-color-scheme:dark){
  body{background:#1c1a17;color:#e9e3d8}.course{border-color:#3a352d}
  a{color:#d6a373}.sub,.place{color:#a59a89}}
</style></head><body>
<h1>Courses</h1>
<p class="sub">Served from your own machine · your place is kept in personal.db</p>
%s
</body></html>
"""

NAV = """<nav class="bristol-study-nav" style="display:flex;gap:18px;flex-wrap:wrap;
  align-items:center;margin:36px 0 0;padding-top:18px;border-top:1px solid var(--rule);
  font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px">%s</nav>"""

SCRIPT = """<script id="bristol-study-progress">
(function(){
  var C=%(course)s, L=%(lesson)d;
  function send(kind, present, item, score){
    return fetch("/api/progress", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({course:C, lesson:L, kind:kind, item:item||"",
                           score:score||null, present:present!==false})});
  }
  window.bristolStudy = {record:send, course:C, lesson:L};
  var box=document.getElementById("studied-box");
  if(box){
    fetch("/api/marks?course="+encodeURIComponent(C)+"&lesson="+L)
      .then(function(r){return r.json();})
      .then(function(d){
        box.checked = (d.marks||[]).some(function(m){return m.kind==="reading";});
      });
    box.addEventListener("change", function(){ send("reading", box.checked); });
  }
})();
</script>"""


def list_page(root: str) -> bytes:
    indexed = {c["name"]: c["has_index"] for c in courses(root)}
    blocks = []
    for c in listing(root)["courses"]:
        where = ("Last opened: lesson %02d" % c["last_opened"]
                 if c["last_opened"] else "Not opened yet")
        links = ['<a class="go" href="/%s/resume">Resume</a>' % c["name"]]
        if indexed.get(c["name"]):
            links.append('<a class="go" href="/%s/index.html">All lessons</a>' % c["name"])
        blocks.append(
            '<div class="course"><h2>%s</h2>'
            '<p class="place">%s · %d lessons · starts at lesson %02d</p>%s</div>'
            % (_escape(c["title"]), where, c["lessons"], c["first"], "".join(links)))
    if not blocks:
        blocks = ['<div class="course"><p class="place">No course has rendered '
                  'output yet. Render one first.</p></div>']
    return (LIST_PAGE % "\n".join(blocks)).encode("utf-8")


def _escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def inject(html: str, course: str, number: int, siblings: list[dict]) -> str:
    """The served lesson page: browser-local progress out, server-kept in."""
    html = LOCAL_SCRIPT.sub("", html)
    numbers = [l["number"] for l in siblings]
    i = numbers.index(number) if number in numbers else -1
    links = ['<a href="/">All courses</a>', '<a href="/%s/index.html">Lessons</a>' % course]
    if i > 0:
        prev = siblings[i - 1]
        links.append('<a href="/%s/%s">← Lesson %02d</a>' % (course, prev["file"], prev["number"]))
    if 0 <= i < len(siblings) - 1:
        nxt = siblings[i + 1]
        links.append('<a href="/%s/%s">Lesson %02d →</a>' % (course, nxt["file"], nxt["number"]))
    block = (NAV % "".join(links)) + SCRIPT % {"course": json.dumps(course), "lesson": number}
    return html.replace("</body>", block + "\n</body>", 1)


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "BristolStudy/1"
    root = ""
    quiet = False

    def log_message(self, fmt, *args):  # noqa: A003
        if not self.quiet:
            super().log_message(fmt, *args)

    # -- replies ----------------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _html(self, body: bytes) -> None:
        self._send(200, body, "text/html; charset=utf-8")

    def _redirect(self, where: str) -> None:
        self.send_response(302)
        self.send_header("Location", where)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _error(self, code: int, message: str) -> None:
        self._send(code, message.encode("utf-8"), "text/plain; charset=utf-8")

    # -- routing ----------------------------------------------------------
    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, unquote, urlparse
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.strip("/").split("/") if p]
        query = parse_qs(u.query)

        if not parts:
            return self._html(list_page(self.root))

        if parts[0] == "api":
            return self._api_get(parts[1:], query)

        course = parts[0]
        if not (Path(self.root) / course / "html").is_dir():
            return self._error(404, "No course named %s" % course)

        if len(parts) == 1:
            return self._redirect("/%s/index.html" % course)
        if len(parts) == 2 and parts[1] == "resume":
            return self._redirect("/%s/%s" % (course, self._resume_file(course)))
        if len(parts) != 2:
            return self._error(404, "Not found")
        return self._file(course, parts[1])

    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def do_POST(self):  # noqa: N802
        from urllib.parse import urlparse
        if urlparse(self.path).path != "/api/progress":
            return self._error(404, "Not found")
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            course = str(body["course"])
            lesson = int(body["lesson"])
            kind = str(body["kind"])
        except (KeyError, TypeError, ValueError) as exc:
            return self._json(400, {"ok": False, "error": "bad request: %s" % exc})

        item = str(body.get("item") or "")
        try:
            if body.get("present", True):
                store.record(course, lesson, kind, item, body.get("score"))
            else:
                store.clear(course, lesson, kind, item)
        except ValueError as exc:
            return self._json(400, {"ok": False, "error": str(exc)})
        return self._json(200, {"ok": True, "course": course, "lesson": lesson,
                                "kind": kind, "item": item})

    # -- the pieces -------------------------------------------------------
    def _api_get(self, rest: list[str], query: dict) -> None:
        if rest == ["place"]:
            course = (query.get("course") or [None])[0]
            return self._json(200, {"places": store.place(course)})
        if rest == ["marks"]:
            try:
                course = query["course"][0]
                lesson = int(query["lesson"][0])
            except (KeyError, IndexError, ValueError):
                return self._json(400, {"ok": False, "error": "course and lesson required"})
            return self._json(200, {"marks": store.marks(course, lesson)})
        return self._json(404, {"ok": False, "error": "no such endpoint"})

    def _resume_file(self, course: str) -> str:
        ls = lessons(self.root, course)
        if not ls:
            return "index.html"
        rows = store.place(course)
        if rows:
            want = int(rows[0]["lesson"])
            for l in ls:
                if l["number"] == want:
                    return l["file"]
        return ls[0]["file"]

    def _file(self, course: str, name: str) -> None:
        hdir = course_dir(self.root, course).resolve()
        target = (hdir / name).resolve()
        if hdir not in target.parents or not target.is_file():
            return self._error(404, "No such file in %s" % course)

        if target.suffix.lower() != ".html":
            ctype = {".css": "text/css", ".js": "text/javascript",
                     ".png": "image/png", ".jpg": "image/jpeg",
                     ".jpeg": "image/jpeg", ".gif": "image/gif",
                     ".svg": "image/svg+xml"}.get(target.suffix.lower(),
                                                  "application/octet-stream")
            return self._send(200, target.read_bytes(), ctype)

        html = target.read_text(encoding="utf-8", errors="replace")
        m = LESSON_FILE.match(name)
        if m:
            number = int(m.group("number"))
            # Serving the page is the learner opening it, so the place is kept
            # by the server rather than by a script the browser might not run.
            store.record(course, number, "opened")
            html = inject(html, course, number, lessons(self.root, course))
        elif name == "index.html":
            html = html.replace(
                "</body>",
                (NAV % '<a href="/">All courses</a><a href="/%s/resume">Resume</a>' % course)
                + "\n</body>", 1)
        return self._html(html.encode("utf-8"))


def make_server(root: str, host: str, port: int, quiet: bool = False) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"root": root, "quiet": quiet})
    return ThreadingHTTPServer((host, port), handler)


# ---------------------------------------------------------------------------
# The listing
# ---------------------------------------------------------------------------

def listing(root: str) -> dict:
    """Every course, how many lessons it has, and where it was left."""
    places = {p["course"]: p for p in store.place()}
    out = []
    for c in courses(root):
        p = places.get(c["name"])
        out.append({
            "name": c["name"],
            "title": c["title"],
            "lessons": len(c["lessons"]),
            "first": c["lessons"][0]["number"],
            "last_opened": int(p["lesson"]) if p else None,
            "last_opened_at": p["recorded_at"] if p else None,
        })
    return {"root": str(root), "courses": out}


# ---------------------------------------------------------------------------
# The self-check
# ---------------------------------------------------------------------------

def self_check(root: str) -> int:
    """Start, serve one lesson page, write one progress row, read it back."""
    import tempfile

    failures: list[str] = []

    def ok(line: str) -> None:
        print("ok  [study_server] %s" % line)

    def fail(line: str) -> None:
        print("FAIL [study_server] %s" % line)
        failures.append(line)

    found = courses(root)
    if not found:
        fail("no course under %s has rendered output to serve" % root)
        return 1
    course = found[0]
    lesson = course["lessons"][0]
    ok("%d course(s) discovered; checking %s lesson %02d"
       % (len(found), course["name"], lesson["number"]))

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["PERSONAL_DB_DIR"] = tmp  # a throwaway store; the real one is untouched
        srv = make_server(root, "127.0.0.1", 0, quiet=True)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        try:
            page = _get(base + "/%s/%s" % (course["name"], lesson["file"]))
            if page is None:
                fail("the lesson page did not answer")
            else:
                ok("the lesson page answered, %d bytes" % len(page))
                raw = TOKEN.findall(page)
                if raw:
                    fail("the page carries raw template tokens: %s" % ", ".join(sorted(set(raw))))
                else:
                    ok("no raw template token in the served page")
                if INJECTION_MARK not in page:
                    fail("the page carries no progress layer")
                else:
                    ok("the page carries its progress layer")
                if "localStorage" in page:
                    fail("the page still keeps progress in the browser")
                else:
                    ok("browser-local progress is gone from the page")

            listing = _get(base + "/")
            if listing is None or "Courses" not in listing:
                fail("the course list did not answer")
            else:
                ok("the course list answered")

            wrote = _post(base + "/api/progress",
                          {"course": course["name"], "lesson": lesson["number"],
                           "kind": "opened"})
            if not (wrote or {}).get("ok"):
                fail("the progress write was refused")
            else:
                ok("one progress write accepted")
                back = _get_json(base + "/api/place?course=" + course["name"])
                places = (back or {}).get("places") or []
                if not places or int(places[0]["lesson"]) != lesson["number"]:
                    fail("the write did not read back")
                else:
                    ok("the write read back as lesson %02d" % int(places[0]["lesson"]))
        finally:
            srv.shutdown()
            srv.server_close()

    if failures:
        print("study_server self-check: %d failure(s)" % len(failures))
        return 1
    print("study_server self-check: all green")
    return 0


def _get(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — a check reports the failure rather than raising
        return None


def _get_json(url: str) -> dict | None:
    body = _get(url)
    try:
        return json.loads(body) if body else None
    except ValueError:
        return None


def _post(url: str, payload: dict) -> dict | None:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Serve the rendered courses and keep the learner's place.")
    p.add_argument("--course", help="land on where this course was left")
    p.add_argument("--base", help="the courses root, used as written")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--self-check", action="store_true", dest="self_check")
    p.add_argument("--list-json", action="store_true", dest="list_json",
                   help="print the course listing and exit")
    args = p.parse_args(argv)

    try:
        root = args.base or render.courses_root()
    except SystemExit as exc:  # the resolver names the key it wanted
        print(str(exc), file=sys.stderr)
        return 2
    if not Path(root).is_dir():
        print("No courses root at %s" % root, file=sys.stderr)
        return 2

    if args.list_json:
        found = listing(root)
        if not found["courses"]:
            print("No course under %s has rendered output." % root, file=sys.stderr)
            return 2
        print(json.dumps(found))
        return 0

    if args.self_check:
        return self_check(root)

    if args.course and not (Path(root) / args.course / "html").is_dir():
        print("No rendered output for course %s" % args.course, file=sys.stderr)
        return 2

    srv = make_server(root, args.host, args.port)
    landing = "/%s/resume" % args.course if args.course else "/"
    print("Study server on http://%s:%d%s" % (args.host, srv.server_address[1], landing),
          flush=True)
    print("Courses root: %s" % root, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
