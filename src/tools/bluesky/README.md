# Bluesky Tools

Copy an AT Protocol account's posts into the Markdown notebook, one page per day
the account posted, and keep a copy of what was read so that a page outlives the
posts it was made from. The design and the reasoning behind it are the project note
the epic's cards link to; this states what the programs are and how they are
run.

Every call that reads the account is public and unauthenticated: no password,
no API key and no developer account is involved. `purge.py` is the one program
that signs in, because removing a record is a write, and it uses an app
password created for it and revocable on its own.

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

**A run reads the account, adds what it read to the store, and writes the pages
from the store.** The network decides what the store gains; it never decides
what a page loses.

**The one-time copy and the recurring copy are the same run.** Only the date
window differs, so nothing about the backfill can drift from what runs daily.

**A page is written whole, and only when its contents would differ.** An
interrupted run is restarted rather than repaired.

### store.py

The account's own copy, in `data/<instance>/bluesky/archive.db`: every post
record the account has been seen to hold, and each pruned conversation as it was
last seen whole.

**The store only gains.** A post already kept is refreshed in place and never
removed, and a conversation is replaced only by a newly fetched one holding
every one of the account's posts the kept copy held. A thread that comes back
short, for whatever reason, leaves what is kept alone.

**A conversation is kept as the page needs it.** A post as the app view returns
it also carries avatars, counts, labels and viewer state that no page reads;
what is stored is the words and whatever the post carried with them.

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

### purge.py

Empties the account: every post and every repost, and nothing else. Bare, it
prints what it would remove and removes nothing; `--delete` does it.

**The store is read before the account is written.** Every record the pass is
about to remove is kept first, and the moment each delete is sent is written
down before it is sent, so a pass cut off partway says what is already gone and
resumes from there rather than starting again.

**It holds to the account's write budget** — 5,000 points an hour and 35,000 a
day, at one point a delete — so the whole corpus goes inside two hours, and
`--budget SECONDS` stops it early and says what is left.

**Followers are untouched.** A follow is a record in the follower's own
repository pointing at this account, so nothing the account deletes can reach
one. The count is read before and after and both are printed.

**What is still served is asked for again.** A data server that has accepted a
delete and an app view that has not yet seen it disagree, and a reader believes
the app view, so the check is what the public view serves rather than what the
delete call returned.

### judge.py

Sorts every post the account made into what the notebook keeps. The program
does not judge: it hands a reader the posts in one fixed order with the
conversation each one sat in, takes a verdict back, and keeps the verdicts in
`data/<instance>/bluesky/verdicts.db`.

```
python3 src/tools/bluesky/judge.py status
python3 src/tools/bluesky/judge.py batch --from 0 --count 70
python3 src/tools/bluesky/judge.py record --file verdicts.txt
python3 src/tools/bluesky/judge.py sample --count 100 --seed 7
python3 src/tools/bluesky/judge.py compare
```

**A post's number is its position in the corpus**, ordered by when it was
posted, so two runs hand the same reader the same numbers and a verdict can be
recorded by number rather than by address.

**The standard `batch` prints is the only standard.** `--bare` leaves it out
for a reader already holding it.

**A conversation is printed once, with every post of the account's being
judged inside it numbered.** `--unjudged` skips posts already judged, which is
what makes a pass resumable; those posts stay in the conversation as context.

**`sample` hands back judged posts without their verdicts**, so a second
reader judges blind; `record --table review` keeps that second reading, and
`compare` counts where the two differ. A check shown the judgment it is
checking is not a check.

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
| `app_password` | the app password `purge.py` signs in with, and nothing else |

**A page's filename carries a prefix.** Obsidian resolves a link by basename, so
a page named for a date alone would collide with the journal's own note for that
date and make every link to either one ambiguous.

## What is checked

```
python3 src/tools/test_tools/smoke.py bluesky_pruning bluesky_archive bluesky_purge
```

`bluesky_pruning` is six conversations built by hand: branch pruning, two
answered branches arriving as one tree, the cap at two values, a deleted post
kept as a placeholder, a thread the account is not in, and a thread whose root
is gone.

`bluesky_archive` is the store against an account read twice, the second read
shorter than the first: a post no longer served stays, a day the window opens
partway through comes back whole, and a conversation is never traded for one
holding less of what the account said.

`bluesky_purge` is the arithmetic that paces a deletion pass and the record
that lets a cut-off one resume. It reaches no account.
