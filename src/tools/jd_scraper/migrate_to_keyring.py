#!/usr/bin/env python3
"""
migrate_to_keyring.py
One-time migration: reads the plaintext credential files and writes them
into macOS Keychain via the `keyring` library.

Run once from this agent's provisioned tools root:
  python3 tools/migrate_to_keyring.py

After confirming all entries are readable, manually delete the source files:
  rm <CAREER_COACH_DIR>/config/gmail_credentials.json
  rm <CAREER_COACH_DIR>/config/gmail_token.json

credentials.json should already be scrubbed (passwords replaced with
"stored in macOS Keychain" markers) — no delete needed there.
"""

import json
import sys
from pathlib import Path

import keyring

# ---------------------------------------------------------------------------
# Paths (relative to this script's directory → project root is one level up)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"

GMAIL_CREDS_FILE = CONFIG_DIR / "gmail_credentials.json"
GMAIL_TOKEN_FILE = CONFIG_DIR / "gmail_token.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

KEYRING_SERVICE = "career_coach"

ENTRIES = {
    "gmail_credentials_json": GMAIL_CREDS_FILE,
    "gmail_token_json": GMAIL_TOKEN_FILE,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def store(key: str, value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, key, value)
    # Verify immediately
    retrieved = keyring.get_password(KEYRING_SERVICE, key)
    if retrieved != value:
        print(f"  ERROR: round-trip verification failed for '{key}'")
        sys.exit(1)
    print(f"  OK: '{key}' stored and verified.")


def migrate_json_file(key: str, path: Path) -> None:
    if not path.exists():
        print(f"  SKIP: {path} not found (already migrated or doesn't exist).")
        return
    raw = path.read_text(encoding="utf-8").strip()
    # Validate it's parseable JSON before storing
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ERROR: {path} is not valid JSON: {e}")
        sys.exit(1)
    store(key, raw)


def migrate_credential_passwords() -> None:
    if not CREDENTIALS_FILE.exists():
        print(f"  SKIP: {CREDENTIALS_FILE} not found.")
        return
    with open(CREDENTIALS_FILE, "r") as f:
        creds = json.load(f)

    migrated = []
    for site, key_name in [("flexjobs", "flexjobs_password"), ("linkedin", "linkedin_password")]:
        entry = creds.get(site, {})
        password = entry.get("password", "")
        if not password or password.startswith("stored in"):
            print(f"  SKIP: {site} password already migrated or empty.")
            continue
        store(key_name, password)
        migrated.append(site)

    if migrated:
        print(f"  Migrated passwords for: {', '.join(migrated)}")
    else:
        print("  No new passwords to migrate from credentials.json.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Migrating career_coach secrets to macOS Keychain (service='{KEYRING_SERVICE}')...")
    print()

    print("1. Gmail OAuth2 client credentials (gmail_credentials.json):")
    migrate_json_file("gmail_credentials_json", GMAIL_CREDS_FILE)

    print()
    print("2. Gmail OAuth2 token (gmail_token.json):")
    migrate_json_file("gmail_token_json", GMAIL_TOKEN_FILE)

    print()
    print("3. Job-board passwords (credentials.json):")
    migrate_credential_passwords()

    print()
    print("Migration complete. All entries stored and verified.")
    print()
    print("Next steps:")
    print("  1. Run gmail_harvest.py once to confirm OAuth flow works from keychain.")
    print("  2. Then delete the plaintext source files:")
    print("       rm <CAREER_COACH_DIR>/config/gmail_credentials.json")
    print("       rm <CAREER_COACH_DIR>/config/gmail_token.json")
    print("  3. Remove the gitignore entries for those files (they no longer exist).")


if __name__ == "__main__":
    main()
