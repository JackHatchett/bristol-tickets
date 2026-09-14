"""Read an AT Protocol account's public post records.

Every call here is public and unauthenticated. The account's own personal data
server is the authority on what it posted; the app view is the authority on what
a conversation looks like.
"""

from __future__ import annotations

import json
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
            with urllib.request.urlopen(request, timeout=30) as response:
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
    collected = []
    cursor = None
    while True:
        params = {"repo": did, "collection": POST_COLLECTION, "limit": PAGE_SIZE}
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
