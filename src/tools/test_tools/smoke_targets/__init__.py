"""smoke_targets — one module per smoke target.

Each module ``smoke_targets/check_<target>.py`` defines ``check_<target>()``,
which returns the lines a passing run prints and raises ``SmokeFailure`` on a
failed check. ``smoke.py`` imports a target's module only in the subprocess
that runs it, so one target's imports never reach another's process.
"""
