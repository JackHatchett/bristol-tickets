"""Read an AT Protocol account's public post records.

Every call here is public and unauthenticated. The account's own personal data
server is the authority on what it posted; the app view is the authority on what
a conversation looks like.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

APPVIEW = "https://public.api.bsky.app"
PLC_DIRECTORY = "https://plc.directory"
POST_COLLECTION = "app.bsky.feed.post"

PAGE_SIZE = 100
MAX_ATTEMPTS = 5
FIRST_BACKOFF_SECONDS = 2.0
USER_AGENT = "bristol-bluesky-sync/1 (+https://github.com/)"


class BlueskyError(RuntimeError):
    """A call did not succeed after every retry it was allowed."""


KEYCHAIN = "/System/Library/Keychains/SystemRootCertificates.keychain"

_context = None


def certificate_authorities():
    """One TLS context holding whatever certificate authorities this machine
    has, from the first source that offers any.

    An interpreter is free to ship without a trust store of its own, and one
    launched by a schedule inherits no shell's environment, so the sources are
    tried in turn rather than assumed: the interpreter's own store, the certifi
    package, the paths OpenSSL was built to read, and on macOS the system root
    keychain, exported as certificates in the form load_verify_locations takes.
    A context with no authority in it verifies nothing, so the search ends at
    the first one that has any.
    """
    global _context
    if _context is not None:
        return _context
    context = ssl.create_default_context()
    if not context.cert_store_stats()["x509_ca"]:
        try:
            import certifi

            context.load_verify_locations(certifi.where())
        except Exception:
            pass
    if not context.cert_store_stats()["x509_ca"]:
        paths = ssl.get_default_verify_paths()
        for candidate in (paths.cafile, paths.openssl_cafile):
            if candidate and os.path.exists(candidate):
                try:
                    context.load_verify_locations(candidate)
                    break
                except OSError:
                    continue
    if not context.cert_store_stats()["x509_ca"] and sys.platform == "darwin":
        exported = subprocess.run(
            ["/usr/bin/security", "find-certificate", "-a", "-p", KEYCHAIN],
            capture_output=True, text=True)
        if exported.returncode == 0 and exported.stdout.strip():
            context.load_verify_locations(cadata=exported.stdout)
    if not context.cert_store_stats()["x509_ca"]:
        raise BlueskyError(
            "this interpreter has no certificate authorities to verify a "
            "server with; install certifi for it, or run its own certificate "
            "installer")
    _context = context
    return _context


def _get(url, params=None, attempts=MAX_ATTEMPTS):
    """One GET returning parsed JSON, retrying a throttle or a server fault.

    A short result read as a quiet day is the failure this guards against, so a
    call that never succeeds raises rather than returning nothing.
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    delay = FIRST_BACKOFF_SECONDS
    last = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(
                    request, timeout=30,
                    context=certificate_authorities()) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last = error
            if error.code == 429 or error.code >= 500:
                retry_after = error.headers.get("retry-after") if error.headers else None
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                time.sleep(wait)
                delay *= 2
                continue
            raise BlueskyError(f"{error.code} from {url}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last = error
            time.sleep(delay)
            delay *= 2
    raise BlueskyError(f"gave up on {url} after {attempts} attempts: {last}")


def resolve_handle(handle):
    """The account identifier behind a handle."""
    payload = _get(f"{APPVIEW}/xrpc/com.atproto.identity.resolveHandle", {"handle": handle})
    did = payload.get("did")
    if not did:
        raise BlueskyError(f"no account identifier for handle {handle}")
    return did


def resolve_pds(did):
    """The host serving an account's own records."""
    if did.startswith("did:plc:"):
        document = _get(f"{PLC_DIRECTORY}/{did}")
    elif did.startswith("did:web:"):
        host = urllib.parse.unquote(did[len("did:web:"):]).replace(":", "/")
        document = _get(f"https://{host}/.well-known/did.json")
    else:
        raise BlueskyError(f"unsupported account identifier {did}")
    for service in document.get("service") or []:
        if service.get("id", "").endswith("#atproto_pds"):
            endpoint = service.get("serviceEndpoint")
            if endpoint:
                return endpoint.rstrip("/")
    raise BlueskyError(f"no data server named in the document for {did}")


def resolve_account(handle):
    """Both halves of an account's address, from its handle alone."""
    did = resolve_handle(handle)
    return did, resolve_pds(did)


def created_at(record):
    """A post record's creation time, as an aware datetime in UTC."""
    raw = (record.get("value") or {}).get("createdAt") or ""
    text = raw.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        raise BlueskyError(f"unreadable timestamp {raw!r}")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def read_posts(did, pds, since=None, progress=None):
    """Every post the account created, oldest first.

    `since` is an aware datetime; paging stops as soon as it has passed it, so a
    daily run walks one page rather than the whole repository. A repost is a
    different record type and never appears here.
    """
    return read_records(did, pds, POST_COLLECTION, since=since, progress=progress)


def read_records(did, pds, collection, since=None, progress=None):
    """Every record the account holds in one collection, oldest first."""
    collected = []
    cursor = None
    while True:
        params = {"repo": did, "collection": collection, "limit": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        page = _get(f"{pds}/xrpc/com.atproto.repo.listRecords", params)
        records = page.get("records") or []
        if not records:
            break
        passed_the_window = False
        for record in records:
            if since is not None and created_at(record) < since:
                passed_the_window = True
                continue
            collected.append(record)
        if progress:
            progress(len(collected))
        cursor = page.get("cursor")
        if passed_the_window or not cursor:
            break
    collected.sort(key=created_at)
    return collected


def get_thread(uri, depth=100, parent_height=100):
    """A conversation tree around one post, or None where it is unreachable."""
    try:
        payload = _get(
            f"{APPVIEW}/xrpc/app.bsky.feed.getPostThread",
            {"uri": uri, "depth": depth, "parentHeight": parent_height},
        )
    except BlueskyError:
        return None
    return payload.get("thread")


def profile(actor):
    """An account's public profile, which is where its follower count is."""
    return _get(f"{APPVIEW}/xrpc/app.bsky.actor.getProfile", {"actor": actor})


def author_feed(actor, limit=25):
    """What the app view serves for an account, which is what a reader sees.

    The account's own data server is the authority on what it holds; this is
    the authority on what anyone else can still read, and the two can disagree
    for as long as it takes an indexer to catch up.
    """
    payload = _get(f"{APPVIEW}/xrpc/app.bsky.feed.getAuthorFeed",
                   {"actor": actor, "limit": limit})
    return payload.get("feed") or []
