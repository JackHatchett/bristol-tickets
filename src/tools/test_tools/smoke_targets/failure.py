"""smoke_targets/failure.py — the exception a smoke target raises for a failed check."""

from __future__ import annotations


class SmokeFailure(RuntimeError):  # noqa: N818 (named for what a check reports)
    pass
