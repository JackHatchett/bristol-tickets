#!/usr/bin/env python3
"""quiz.py — a quiz's multiple-choice questions, as data a page can check.

Input is a quiz's Markdown. Operation is a parse of its numbered questions, its
lettered options and its answer key. Output is the questions rendered as
answerable blocks, each carrying its own correct letter and the explanation the
key already gives, with everything the parse did not recognise passed through as
prose.

Standard library only, as the renderer is.

The corpus writes a question, an option and a key entry several ways, and all of
them are read here:

    **1. Question text**        **1.** Question text        **Q1.** Question text
    a) Option                   - (a) Option                - A. Option

The correct letter comes from the answer key, from an **Answer: b** line under
the options, or from a ✓ on the option itself. The key is read in four shapes:

    | 1 | **b** | Why |         **Question 1 — B**
    **1. (c) Text.** Why       1. **B** — Why

- **A question is interactive only where the parse found options and a key
  letter naming one of them.** Everything else keeps the rendering it had:
  short-answer questions, a quiz with no key, a dialect nobody has written yet.
- **The answer key is still rendered.** It carries the model answers to the
  short-answer questions, which no machine marks, so removing it would lose
  them.
"""

from __future__ import annotations

import html
import re

# **1. Question text**  — the whole question inside one bold run.
Q_BOLD = re.compile(r"^\*\*(?:Q(?:uestion)?\s*)?(\d+)[.)]\s+(.*?)\*\*\s*$")
# **1.** Question text  — the number bold, the question beside it.
Q_LEAD = re.compile(r"^\*\*(?:Q(?:uestion)?\s*)?(\d+)[.)]?\*\*\s*(.*)$")
# a) Option   - (a) Option   - A. Option
OPTION = re.compile(r"^\s*(?:[-*+]\s+)?(?:\(([A-Za-z])\)|([A-Za-z])[).\]])\s+(.+?)\s*$")
# The key's own heading, and the two shapes an entry under it takes.
KEY_HEADING = re.compile(r"^#{1,6}\s+(?:answer key|answers?)\s*$", re.IGNORECASE | re.MULTILINE)
KEY_ROW = re.compile(
    r"^\s*\|\s*(?:Q(?:uestion)?\s*)?(\d+)\s*\|\s*\**\(?([A-Za-z])\)?\**\s*\|\s*(.*?)\s*\|\s*$")
KEY_LEAD = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
KEY_LIST = re.compile(
    r"^\s*(\d+)[.)]\s+(?:\*\*\(?([A-Za-z])\)?\*\*|\(([A-Za-z])\))\s*[—–:-]*\s*(.*)$")
# 1. B — explanation. The separator is required: without it every ordinary
# numbered list item would read as an answer whose letter is its first word's.
KEY_PLAIN = re.compile(r"^\s*(\d+)[.)]\s+([A-Za-z])\s*[—–:-]\s+(.*)$")
# **Answer: b** — the key of a quiz that keeps no key section.
ANSWER_INLINE = re.compile(r"^\*\*Answers?:?\s*\(?([A-Za-z])\)?\.?\*\*\s*$")
TICK = "\u2713"
KEY_NAMES = re.compile(r"^(?:Question\s*|Q)?(\d+)\s*[.)]?\s*[—–-]?\s*\(?([A-Za-z])\)?[.)]?\s*(.*)$")

HEADING = re.compile(r"^#{1,6}\s+")
RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")

DRILL_MARK = "<!--DRILL-MARK-->"


class Question:
    """One numbered question, and what the key says about it."""

    def __init__(self, number: int, prompt: str, start: int) -> None:
        self.number = number
        self.prompt = prompt
        self.options: list[tuple[str, str]] = []
        self.answer = ""
        self.why = ""
        self.start = start
        self.end = start

    @property
    def markable(self) -> bool:
        return bool(self.options) and self.answer.lower() in {
            letter.lower() for letter, _ in self.options}


# ---------------------------------------------------------------------------
# The parse
# ---------------------------------------------------------------------------

def split_key(md: str) -> tuple[str, str]:
    """The quiz body, and its answer key with the key's own heading."""
    found = KEY_HEADING.search(md)
    if not found:
        return md, ""
    return md[:found.start()], md[found.start():]


def read_questions(body: str) -> list[Question]:
    """Every numbered question in the body, with the options under it."""
    lines = body.split("\n")
    out: list[Question] = []
    current: Question | None = None
    reading_prompt = False
    for i, line in enumerate(lines):
        bold = Q_BOLD.match(line)
        lead = None if bold else Q_LEAD.match(line)
        if bold or lead:
            m = bold or lead
            current = Question(int(m.group(1)), m.group(2).strip(), i)
            current.end = i
            reading_prompt = not bool(bold)
            out.append(current)
            continue
        if current is None:
            continue
        option = OPTION.match(line)
        if option:
            letter = option.group(1) or option.group(2)
            text = option.group(3)
            if TICK in text:
                current.answer = letter
                text = text.replace(TICK, "").strip()
            current.options.append((letter, text))
            current.end = i
            reading_prompt = False
            continue
        inline_answer = ANSWER_INLINE.match(line.strip())
        if inline_answer and current.options:
            current.answer = inline_answer.group(1)
            current.end = i
            reading_prompt = False
            continue
        if not line.strip():
            reading_prompt = False
            continue
        if HEADING.match(line) or RULE.match(line):
            current = None
            continue
        if reading_prompt:
            # A prompt that wraps onto the next line, which the corpus does.
            current.prompt += " " + line.strip()
            current.end = i
    return out


def read_key(key: str) -> dict[int, tuple[str, str]]:
    """What the key says: question number to (letter, explanation)."""
    out: dict[int, tuple[str, str]] = {}
    lines = key.split("\n")
    for i, line in enumerate(lines):
        row = KEY_ROW.match(line)
        if row:
            out.setdefault(int(row.group(1)), (row.group(2), row.group(3)))
            continue
        listed = KEY_LIST.match(line)
        if listed:
            out.setdefault(int(listed.group(1)),
                           (listed.group(2) or listed.group(3), listed.group(4)))
            continue
        plain = KEY_PLAIN.match(line)
        if plain:
            out.setdefault(int(plain.group(1)), (plain.group(2), plain.group(3)))
            continue
        lead = KEY_LEAD.match(line)
        if not lead:
            continue
        named = KEY_NAMES.match(lead.group(1).strip())
        if not named:
            continue
        number = int(named.group(1))
        if number in out:
            continue
        # The explanation is what the entry says after the letter, plus the
        # rest of its paragraph.
        tail = [t for t in (named.group(3).strip(), lead.group(2).strip()) if t]
        j = i + 1
        while j < len(lines) and lines[j].strip() and not KEY_LEAD.match(lines[j]) \
                and not KEY_ROW.match(lines[j]) and not HEADING.match(lines[j]) \
                and not RULE.match(lines[j]) and not lines[j].strip().startswith(":::"):
            tail.append(lines[j].strip())
            j += 1
        out[number] = (named.group(2), " ".join(tail))
    return out


def parse(md: str) -> tuple[list[Question], str, str]:
    """The questions, the body they came from, and the key."""
    body, key = split_key(md)
    questions = read_questions(body)
    answers = read_key(key)
    for question in questions:
        letter, why = answers.get(question.number, ("", ""))
        question.answer = letter or question.answer
        question.why = why
    return questions, body, key


# ---------------------------------------------------------------------------
# The rendering
# ---------------------------------------------------------------------------

def _block(question: Question, to_html, inline) -> str:
    options = "\n".join(
        '    <li><button type="button" class="quiz-opt" data-opt="%s">'
        '<span class="quiz-letter">%s</span> %s</button></li>'
        % (html.escape(letter.lower(), quote=True), html.escape(letter), inline(text))
        for letter, text in question.options)
    why = ('  <div class="quiz-why" hidden>%s</div>' % to_html(question.why)) \
        if question.why else ""
    return "\n".join(x for x in [
        '<div class="quiz-q" data-q="%d" data-answer="%s">'
        % (question.number, html.escape(question.answer.lower(), quote=True)),
        '  <p class="quiz-prompt"><strong>%d.</strong> %s</p>'
        % (question.number, inline(question.prompt)),
        '  <ul class="quiz-options">', options, '  </ul>',
        '  <p class="quiz-verdict" hidden></p>',
        why,
        '</div>'] if x)


def render(md: str, to_html, inline, fallback) -> str:
    """The quiz as an answerable page, or exactly what it rendered as before.

    ``fallback`` is what renders a quiz no question of which could be marked, so
    an unrecognised dialect loses nothing.
    """
    questions, body, key = parse(md)
    markable = [q for q in questions if q.markable]
    if not markable:
        return fallback(md)

    lines = body.split("\n")
    spans = {q.start: q for q in markable}
    ends = {q.start: q.end for q in markable}
    out: list[str] = []
    prose: list[str] = []
    i = 0
    while i < len(lines):
        if i in spans:
            if prose:
                out.append(to_html("\n".join(prose)))
                prose = []
            out.append(_block(spans[i], to_html, inline))
            i = ends[i] + 1
            continue
        prose.append(lines[i])
        i += 1
    if prose:
        out.append(to_html("\n".join(prose)))

    if key:
        if ":::answer" in md:
            out.append(to_html(key))
        else:
            heading, _, rest = key.partition("\n")
            out.append('<details class="answer"><summary>Show answer key</summary>'
                       '<div class="answer-content">\n%s\n</div></details>' % to_html(rest))
    return ('<div class="quiz" data-count="%d">\n%s\n</div>'
            % (len(markable), "\n".join(out)))
