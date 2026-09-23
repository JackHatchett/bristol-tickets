#!/usr/bin/env python3
"""
keyring_utils.py
career_coach's secrets, read and written through the shared keychain module,
src/tools/_shared/keychain.py, which is the one place this system touches the
operating system's store. What lives here is what career_coach alone knows: the
names its secrets are kept under, and that two of them are JSON blobs.

All secrets live under service name KEYRING_SERVICE ("career_coach").
Keys stored:
  gmail_credentials_json  — full JSON blob from gmail_credentials.json (OAuth2 client secrets)
  gmail_token_json        — full JSON blob from gmail_token.json (OAuth2 access/refresh token)
  <site>_username, <site>_password — a job board's sign-in, for ziprecruiter,
                            flexjobs, indeed and linkedin; jd_scraper.py --login
                            fills them in

Usage:
  from keyring_utils import get_secret, set_secret, get_gmail_credentials, get_gmail_token, save_gmail_token

A missing secret is stored with:
  python3 src/tools/_shared/keychain.py set career_coach <key>
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import keychain  # noqa: E402  (the shared keychain reader)

KEYRING_SERVICE = "career_coach"

# ----- low-level helpers -----------------------------------------------------

def get_secret(key: str) -> str:
    """Return the secret stored at (KEYRING_SERVICE, key), or raise if missing."""
    value = keychain.read(KEYRING_SERVICE, key)
    if value is None:
        raise KeyError(
            f"No keyring entry found for service='{KEYRING_SERVICE}' key='{key}'. "
            f"Store it with: python3 src/tools/_shared/keychain.py set "
            f"{KEYRING_SERVICE} {key}"
        )
    return value


def set_secret(key: str, value: str) -> None:
    """Store value at (KEYRING_SERVICE, key) in the keychain."""
    keychain.write(KEYRING_SERVICE, key, value)


def delete_secret(key: str) -> None:
    """Remove a keyring entry. Safe to call even if the key doesn't exist."""
    keychain.erase(KEYRING_SERVICE, key)


# ----- Gmail credentials (OAuth2 client secrets) -----------------------------

def get_gmail_credentials() -> dict:
    """
    Return the parsed gmail_credentials dict (the 'installed' key contents).
    This is what InstalledAppFlow.from_client_config() expects.
    """
    raw = get_secret("gmail_credentials_json")
    return json.loads(raw)


def set_gmail_credentials(creds_dict: dict) -> None:
    """Store the gmail_credentials dict (top-level, including the 'installed' key)."""
    set_secret("gmail_credentials_json", json.dumps(creds_dict))


# ----- Gmail token (OAuth2 access + refresh token) ---------------------------

def get_gmail_token() -> dict:
    """
    Return the parsed gmail_token dict.
    This is what Credentials.from_authorized_user_info() expects.
    """
    raw = get_secret("gmail_token_json")
    return json.loads(raw)


def save_gmail_token(token_json_str: str) -> None:
    """
    Persist a refreshed token back to the keychain.
    Pass creds.to_json() directly — it returns a JSON string.
    """
    set_secret("gmail_token_json", token_json_str)


def gmail_token_exists() -> bool:
    """Return True if a gmail token is already stored in the keychain."""
    return keychain.read(KEYRING_SERVICE, "gmail_token_json") is not None


# ----- Job-board passwords ---------------------------------------------------

def get_flexjobs_password() -> str:
    return get_secret("flexjobs_password")


def get_linkedin_password() -> str:
    return get_secret("linkedin_password")
