# Bluesky Tools

Copy an AT Protocol account's posts into the Markdown notebook, one page per day
the account posted. The design and the reasoning behind it are the project note
the epic's cards link to; this states what the programs are and how they are
run.

Every call these make is public and unauthenticated. No password, no app
password, no API key and no developer account is involved, and nothing here
signs in.

## The programs

### sync.py

The whole job, and the only entry point.

```
python3 src/tools/bluesky/sync.py --days 7      # the recurring copy
python3 src/tools/bluesky/sync.py --all         # the whole history
```

- `--dry-run` says what it would write and writes nothing.
- `--skip-existing` leaves a day whose page is already there.
- `--from YYYY-MM-DD` begins at a date rather than the first.
- `--budget SECONDS` stops after that long and names the day it stopped at, for
  a host that will not hold a long-running command.

**The one-time copy and the recurring copy are the same run.** Only the date
window differs, so nothing about the backfill can drift from what runs daily.

**A page is written whole, and only when its contents would differ.** An
interrupted run is restarted rather than repaired.

### client.py

Reads the account. `resolve_account` turns a handle into the account identifier
and the host serving its records. `read_posts` pages
`com.atproto.repo.listRecords` on that host, oldest first, stopping early for a
date window. `get_thread` fetches a conversation from the app view.

A throttle or a server fault is retried with a doubling delay, and a call that
still fails raises rather than returning a short result that would read as a
quiet day.

### threads.py

Groups posts by the conversation they belong to and cuts each one back to what
the account was part of. `conversation` is the one function callers need.

### render.py

Turns a pruned conversation into Markdown. A solo post is prose; a conversation
is a nested outline headed by whoever started it.

### install_schedule.py

Writes the operating system's own daily schedule — a launch agent on macOS, a
cron line elsewhere — so the copy runs with nothing conversational in the loop.
Bare, it prints what it would install; `--install` installs it.

**Run it on the machine that will hold the schedule.** It takes the interpreter,
the repository and the log location from where it is running, so a run from
anywhere else writes another machine's paths into the schedule.

## Configuration

Every field is under `bluesky` in `config/config.local.json`, read one key at a
time.

| Key | What it is |
| --- | --- |
| `handle` | the account to read, as its owner signs in |
| `did`, `pds` | the resolved account identifier and its data server, cached |
| `notes_folder` | the declared folder the day pages go in |
| `journal_folder` | the declared folder the journal's daily notes are in |
| `filename_prefix` | what goes in front of the date in a page's filename |
| `timezone` | the zone a post's day is decided in |
| `thread_tail_cap` | how many posts after the account's last word are kept |
| `link_window_days` | how far back a run looks for journal pages written late |
| `link_into_journal` | whether a journal page gains a link back |
| `fetch_workers` | how many days are worked at once |

**A page's filename carries a prefix.** Obsidian resolves a link by basename, so
a page named for a date alone would collide with the journal's own note for that
date and make every link to either one ambiguous.

## What is checked

```
python3 src/tools/test_tools/smoke.py bluesky_pruning
```

Six conversations built by hand: branch pruning, two answered branches arriving
as one tree, the cap at two values, a deleted post kept as a placeholder, a
thread the account is not in, and a thread whose root is gone.
