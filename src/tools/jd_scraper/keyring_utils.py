#!/usr/bin/env python3
"""
keyring_utils.py
Helpers for reading and writing career_coach secrets from/to macOS Keychain.

All secrets live under service name KEYRING_SERVICE ("career_coach").
Keys stored:
  gmail_credentials_json  — full JSON blob from gmail_credentials.json (OAuth2 client secrets)
  gmail_token_json        — full JSON blob from gmail_token.json (OAuth2 access/refresh token)
  flexjobs_password       — FlexJobs account password
  linkedin_password       — LinkedIn account password

Usage:
  from keyring_utils import get_secret, set_secret, get_gmail_credentials, get_gmail_token, save_gmail_token

Install:
  pip install keyring --break-system-packages
"""

import json
import keyring

KEYRING_SERVICE = "career_coach"

# ----- low-level helpers -----------------------------------------------------

def get_secret(key: str) -> str:
    """Return the secret stored at (KEYRING_SERVICE, key), or raise if missing."""
    value = keyring.get_password(KEYRING_SERVICE, key)
    if value is None:
        raise KeyError(
            f"No keyring entry found for service='{KEYRING_SERVICE}' key='{key}'. "
            f"Run migrate_to_keyring.py to populate the keychain."
        )
    return value


def set_secret(key: str, value: str) -> None:
    """Store value at (KEYRING_SERVICE, key) in the macOS Keychain."""
    keyring.set_password(KEYRING_SERVICE, key, value)


def delete_secret(key: str) -> None:
    """Remove a keyring entry. Safe to call even if the key doesn't exist."""
    try:
        keyring.delete_password(KEYRING_SERVICE, key)
    except keyring.errors.PasswordDeleteError:
        pass


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
    return keyring.get_password(KEYRING_SERVICE, "gmail_token_json") is not None


# ----- Job-board passwords ---------------------------------------------------

def get_flexjobs_password() -> str:
    return get_secret("flexjobs_password")


def get_linkedin_password() -> str:
    return get_secret("linkedin_password")
