"""bristol.reports — the analytic report Bristol writes when you Clear Done.

Clearing the Done column is the board's only natural period boundary: a batch
of finished cards leaves the board together, at a moment the user chose. This
package treats that moment the way a commercial delivery tool treats the close
of a sprint or cycle — it measures the batch that just shipped, sets it against
the board's overall health and the previous report, and writes the result as a
Markdown note in the user's notebook.

Layout:
    paths.py    — where the report goes (env -> .local pointer -> config)
    metrics.py  — DB -> a plain dict of computed facts. No I/O, no formatting.
    render.py   — that dict -> Markdown. No DB access, no computation.
    generate.py — orchestration + CLI.

The three-way split is deliberate: metrics can be unit-tested without a
notebook, render can be re-styled without touching a calculation, and the whole
thing is callable from the Qt button, an agent session, or the future Python
head through the same `generate_report`.
"""

from .generate import generate_report  # noqa: F401

__all__ = ["generate_report"]
