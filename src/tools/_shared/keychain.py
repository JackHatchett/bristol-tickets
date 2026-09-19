#!/usr/bin/env python3
"""keychain.py — a secret read from the operating system's own store, at the
moment the program needs it.

A secret lives in the keychain and never in a file — not in config, not in a
tracked file, not in a git-ignored one (`src/templates/identity_template.md`
§The machinery/personal-data split). A program that needs one reads it here, and
one that cannot asks the user rather than storing it.

Reading is non-interactive on a machine whose user is logged in, so a scheduled
job keeps working; a locked keychain fails the read outright rather than running
half-authenticated, which is the answer a caller wants.

    python3 src/tools/_shared/keychain.py set <service> <key>   # prompts, echoes nothing
    python3 src/tools/_shared/keychain.py get <service> <key>
    python3 src/tools/_shared/keychain.py erase <service> <key>
"""

from __future__ import annotations

import getpass
import sys


def _keyring():
    try:
        import keyring
    except ImportError:  # pragma: no cover - the install is the user's machine
        raise SystemExit(
            "this needs the keyring package: pip3 install keyring")
    return keyring


def read(service: str, key: str) -> str | None:
    """The secret, or None where the keychain holds none under that name.

    A machine with no keychain at all is a different answer from a keychain
    with nothing in it — a sandbox, a container, a login that has never
    unlocked one — and it stops here rather than being read as an empty
    keychain, which would send the caller to store a secret where nothing can
    hold it.
    """
    keyring = _keyring()
    try:
        return keyring.get_password(service, key)
    except keyring.errors.NoKeyringError as error:
        raise SystemExit(
            f"this machine has no keychain to read {service} / {key} from "
            f"({error}). Run this on the machine that holds the keychain.")


def write(service: str, key: str, value: str) -> None:
    _keyring().set_password(service, key, value)


def erase(service: str, key: str) -> None:
    keyring = _keyring()
    try:
        keyring.delete_password(service, key)
    except keyring.errors.PasswordDeleteError:
        pass


def require(service: str, key: str, hint: str) -> str:
    """The secret, or an exit telling the user exactly how to put it there.

    A program that needs a secret it cannot find stops with the one command
    that fixes it, because the alternative is a stack trace the user has to
    translate into that command himself.
    """
    value = read(service, key)
    if value:
        return value
    raise SystemExit(
        f"no secret in the keychain under {service} / {key}.\n{hint}\n"
        f"store it with: python3 src/tools/_shared/keychain.py set "
        f"{service} {key}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-3], file=sys.stderr)
        return 2
    action, service, key = argv
    if action == "get":
        value = read(service, key)
        print(value if value else f"nothing under {service} / {key}")
        return 0 if value else 1
    if action == "set":
        # Typed rather than passed, so the secret is not in a shell history.
        write(service, key, getpass.getpass(f"{service} / {key}: "))
        print(f"stored under {service} / {key}")
        return 0
    if action == "erase":
        erase(service, key)
        print(f"removed {service} / {key}")
        return 0
    print(f"unknown action {action!r}; use get, set or erase", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
