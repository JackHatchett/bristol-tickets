#!/usr/bin/env python3
"""Teaching Assistant — deterministic HTML lesson renderer (stdlib only).

Converts a course lesson's three Markdown files (lesson, exercise, quiz) into a
single self-contained HTML file using template.html, then regenerates the
per-course index. No external dependencies, deterministic output, tool-neutral
(supports a future open-source teaching engine).

Usage:
    python3 render.py <course> <NN>      # render one lesson + rebuild index
    python3 render.py <course> all       # render every generated lesson + index
    python3 render.py <course> --index   # rebuild index only
    (optional)  --base /path/to/courses  # override the courses root

Courses root resolution (no personal path hardcoded here):
    1. --base, if passed
    2. $TEACHING_ASSISTANT_COURSES_DIR, if set (see config/config.local.json)
    3. ~/Projects (generic fallback, matches the convention other legacy
       course tooling assumed — override with one of the above if courses
       actually live elsewhere, e.g. a Markdown-notebook project root)

Marker syntax (embed in lesson/exercise/quiz Markdown; all optional):

    :::checkpoint
    Open question that requires articulation, not recall.
    ?? Optional framing hint (a reframe or pointer, not the answer).
    :::

    :::drill Optional Title
    $ command the learner types
    $ another command
    -> expected output
    ?? verification: how to confirm it worked
    :::

    :::answer
    Inline answer content, collapsed behind "Show answer".
    :::

If an exercise/quiz file has no :::answer markers, any "Answer Key" / "Answers"
section is auto-collapsed behind a single reveal.
"""
import sys, os, re, html, json, datetime, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, "template.html")
TODAY = datetime.date.today().isoformat()


# ---------------------------------------------------------------- inline
def _inline(text):
    """Convert inline Markdown to HTML on a single logical line/segment."""
    # Obsidian wiki-links [[path|Display]] or [[path]] -> plain display text.
    # The renderer has no notion of the notebook's other files, so it can't
    # emit a working href; showing the display text (dropping the path) beats
    # leaking raw [[...]] syntax into the reading page.
    text = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                  lambda m: m.group(2) if m.group(2) else m.group(1).rsplit("/", 1)[-1],
                  text)
    # Pull out code spans first so their contents are not further processed.
    spans = []
    def stash(m):
        spans.append(html.escape(m.group(1)))
        return "\x00%d\x00" % (len(spans) - 1)
    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    # links [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: '<a href="%s">%s</a>' % (html.escape(m.group(2), quote=True), m.group(1)),
                  text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)([^*]+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w])_(?!\s)([^_]+?)_(?![\w])", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % spans[int(m.group(1))], text)
    return text


# ---------------------------------------------------------------- markers
def _checkpoint(body):
    lines = body.split("\n")
    prompt, hint = [], []
    in_hint = False
    for ln in lines:
        if ln.lstrip().startswith("??"):
            in_hint = True
            hint.append(ln.lstrip()[2:].strip())
        elif in_hint:
            hint.append(ln)
        else:
            prompt.append(ln)
    out = ['<div class="checkpoint">',
           '  <div class="checkpoint-label">⏸ Pause &amp; Think</div>',
           '  <p class="checkpoint-prompt">%s</p>' % _inline(" ".join(p.strip() for p in prompt if p.strip()))]
    h = " ".join(x.strip() for x in hint if x.strip())
    if h:
        out += ['  <details class="checkpoint-reveal"><summary>See a framing hint</summary>',
                '    <p>%s</p></details>' % _inline(h)]
    out.append('</div>')
    return "\n".join(out)


def _drill(title, body):
    cmds, expected, verify = [], [], []
    for ln in body.split("\n"):
        s = ln.strip()
        if s.startswith("$"):
            cmds.append(s)
        elif s.startswith("->") or s.startswith("=>"):
            expected.append(s[2:].strip())
        elif s.startswith("??"):
            verify.append(s[2:].strip())
        elif s:
            cmds.append(s)
    out = ['<div class="drill">',
           '  <div class="drill-label">⌨ Drill%s</div>' % ((" — " + html.escape(title)) if title else "")]
    if cmds:
        out.append('  <pre><code>%s</code></pre>' % html.escape("\n".join(cmds)))
    if expected:
        out += ['  <details><summary>Show expected output</summary>',
                '    <pre><code>%s</code></pre></details>' % html.escape("\n".join(expected))]
    if verify:
        out.append('  <p class="verify">✓ Verify: %s</p>' % _inline(" ".join(verify)))
    out.append('</div>')
    return "\n".join(out)


def _answer(body):
    return ('<details class="answer"><summary>Show answer</summary>'
            '<div class="answer-content">\n%s\n</div></details>' % md_to_html(body))


# ---------------------------------------------------------------- blocks
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
ULI = re.compile(r"^\s*[-*+]\s+(.*)$")
OLI = re.compile(r"^\s*\d+\.\s+(.*)$")
TROW = re.compile(r"^\s*\|.*\|\s*$")
TSEP = re.compile(r"^\s*\|?[\s:-]*-[\s:|-]*\|?\s*$")


def md_to_html(text):
    lines = text.split("\n")
    out, i, n = [], 0, len(text and lines)
    while i < n:
        line = lines[i]

        # marker blocks  :::type ...  :::
        m = re.match(r"^:::\s*(checkpoint|drill|answer)\s*(.*)$", line.strip())
        if m:
            kind, arg = m.group(1), m.group(2).strip()
            body = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                body.append(lines[i]); i += 1
            i += 1  # closing :::
            body = "\n".join(body)
            out.append(_checkpoint(body) if kind == "checkpoint"
                       else _drill(arg, body) if kind == "drill"
                       else _answer(body))
            continue

        # fenced code
        if line.lstrip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(buf)))
            continue

        if not line.strip():
            i += 1
            continue

        # standalone HTML comment markers (e.g. <!-- ta-nav -->, <!-- ta-rel -->)
        # authored for the notebook viewer, not meant to reach the reading page.
        if re.match(r"^\s*<!--.*-->\s*$", line):
            i += 1
            continue

        if HR.match(line):
            out.append("<hr>"); i += 1; continue

        hm = HEADING.match(line)
        if hm:
            lvl = len(hm.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, _inline(hm.group(2).strip()), lvl))
            i += 1
            continue

        # tables
        if TROW.match(line) and i + 1 < n and TSEP.match(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and TROW.match(lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ["<table>", "<thead><tr>" + "".join("<th>%s</th>" % _inline(c) for c in header) + "</tr></thead>", "<tbody>"]
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
            t += ["</tbody>", "</table>"]
            out.append("\n".join(t))
            continue

        # lists
        if ULI.match(line) or OLI.match(line):
            ordered = bool(OLI.match(line))
            tag = "ol" if ordered else "ul"
            items = []
            pat = OLI if ordered else ULI
            while i < n and pat.match(lines[i]):
                items.append("<li>%s</li>" % _inline(pat.match(lines[i]).group(1).strip()))
                i += 1
            out.append("<%s>\n%s\n</%s>" % (tag, "\n".join(items), tag))
            continue

        # blockquote
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip()); i += 1
            out.append("<blockquote>%s</blockquote>" % _inline(" ".join(buf)))
            continue

        # paragraph
        buf = []
        while i < n and lines[i].strip() and not lines[i].lstrip().startswith("```") \
                and not lines[i].strip().startswith(":::") \
                and not HEADING.match(lines[i]) and not HR.match(lines[i]) \
                and not ULI.match(lines[i]) and not OLI.match(lines[i]) \
                and not lines[i].lstrip().startswith(">") and not TROW.match(lines[i]):
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % _inline(" ".join(buf)))
    return "\n".join(out)


def render_answers_section(md):
    """Auto-collapse an 'Answer Key' / 'Answers' section if no :::answer markers used."""
    if ":::answer" in md:
        return md_to_html(md)
    m = re.search(r"^#{1,6}\s+(answer key|answers?)\s*$", md, re.IGNORECASE | re.MULTILINE)
    if not m:
        return md_to_html(md)
    before, after = md[:m.start()], md[m.start():]
    # drop the heading line itself from `after`
    after = after.split("\n", 1)[1] if "\n" in after else ""
    return (md_to_html(before)
            + '\n<details class="answer"><summary>Show answer key</summary>'
            + '<div class="answer-content">\n%s\n</div></details>' % md_to_html(after))


# ---------------------------------------------------------------- driver
def load_progress(course_dir):
    with open(os.path.join(course_dir, "syllabus", "progress.json")) as f:
        return json.load(f)


def lesson_entry(prog, number):
    for L in prog.get("lessons", []):
        if int(L.get("number")) == int(number):
            return L
    return None


def read_if(path):
    return open(path).read() if os.path.exists(path) else ""


def render_lesson(base, course, number):
    cdir = os.path.join(base, course)
    prog = load_progress(cdir)
    L = lesson_entry(prog, number)
    if not L:
        raise SystemExit("No lesson %s in %s progress.json" % (number, course))
    nn = "%02d" % int(number)
    lesson_md = read_if(os.path.join(cdir, L["lesson_file"]))
    ex_md = read_if(os.path.join(cdir, L.get("exercise_file", "")))
    qz_md = read_if(os.path.join(cdir, L.get("quiz_file", "")))

    # Strip a leading H1 from the lesson body (title comes from the header band).
    lesson_md = re.sub(r"^\s*#\s+.*\n", "", lesson_md, count=1)

    title = L.get("topic") or course
    display = prog.get("course_title", course)

    tpl = open(TEMPLATE_PATH).read()
    out_html = (tpl
        .replace("{{COURSE_DISPLAY_NAME}}", html.escape(display))
        .replace("{{COURSE_NAME}}", html.escape(course))
        .replace("{{LESSON_NUMBER}}", nn)
        .replace("{{LESSON_TITLE}}", html.escape(title))
        .replace("{{CONTENT_WITH_CHECKPOINTS}}", md_to_html(lesson_md) if lesson_md else "<p><em>Lesson not yet generated.</em></p>")
        .replace("{{EXERCISES}}", render_answers_section(ex_md) if ex_md else "<p><em>No exercises generated.</em></p>")
        .replace("{{QUIZ}}", render_answers_section(qz_md) if qz_md else "<p><em>No quiz generated.</em></p>")
        .replace("{{RENDER_DATE}}", TODAY))

    hdir = os.path.join(cdir, "html")
    os.makedirs(hdir, exist_ok=True)
    out_path = os.path.join(hdir, "%s_lesson_%s.html" % (course, nn))
    with open(out_path, "w") as f:
        f.write(out_html)
    return out_path


def build_index(base, course):
    cdir = os.path.join(base, course)
    prog = load_progress(cdir)
    display = prog.get("course_title", course)
    hdir = os.path.join(cdir, "html")
    os.makedirs(hdir, exist_ok=True)
    rows = []
    for L in prog.get("lessons", []):
        nn = "%02d" % int(L["number"])
        fn = "%s_lesson_%s.html" % (course, nn)
        exists = os.path.exists(os.path.join(hdir, fn))
        link = '<a href="%s">%s</a>' % (fn, html.escape(L.get("topic", "Lesson " + nn))) if exists \
               else '<span style="color:#999">%s</span>' % html.escape(L.get("topic", "Lesson " + nn))
        marks = []
        if L.get("lesson_complete"): marks.append("content ✓")
        if L.get("studied"): marks.append("studied ✓")
        if L.get("mastery"): marks.append(html.escape(str(L["mastery"])))
        status = " · ".join(marks) if marks else "&mdash;"
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (nn, link, status))
    page = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s — Index</title>
<style>body{background:#fbfaf7;color:#1f1c18;font-family:Georgia,serif;max-width:740px;margin:0 auto;padding:48px 24px}
h1{font-size:28px}table{border-collapse:collapse;width:100%%;font-size:17px}
th,td{border:1px solid #e4ddd2;padding:8px 12px;text-align:left}th{background:#f1ece3}
a{color:#7a4b2b}.foot{color:#6b6359;font-family:sans-serif;font-size:13px;margin-top:32px}
@media(prefers-color-scheme:dark){body{background:#1c1a17;color:#e9e3d8}th{background:#272320}td,th{border-color:#3a352d}a{color:#d6a373}}</style>
</head><body><h1>%s</h1>
<table><thead><tr><th>#</th><th>Lesson</th><th>Status</th></tr></thead><tbody>
%s
</tbody></table>
<p class="foot">Generated %s · self-contained, no external dependencies</p>
</body></html>""" % (html.escape(display), html.escape(display), "\n".join(rows), TODAY)
    idx = os.path.join(hdir, "index.html")
    with open(idx, "w") as f:
        f.write(page)
    return idx


def main(argv):
    base = os.environ.get("TEACHING_ASSISTANT_COURSES_DIR") or os.path.expanduser("~/Projects")
    if "--base" in argv:
        k = argv.index("--base")
        base = argv[k + 1]
        del argv[k:k + 2]
    if len(argv) < 2:
        raise SystemExit(__doc__)
    course, target = argv[0], argv[1]
    cdir = os.path.join(base, course)
    if target == "--index":
        print("index:", build_index(base, course)); return
    if target == "all":
        prog = load_progress(cdir)
        for L in prog.get("lessons", []):
            if L.get("lesson_generated"):
                print("rendered:", render_lesson(base, course, L["number"]))
    else:
        print("rendered:", render_lesson(base, course, target))
    print("index:", build_index(base, course))


if __name__ == "__main__":
    main(sys.argv[1:])
