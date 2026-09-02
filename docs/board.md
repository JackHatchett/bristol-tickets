# The board

Bristol Tickets is the desktop app: a Kanban board over one SQLite database. Run
it with `python3 src/tools/bristol/app.py`, or from the Dock if you built a
launcher.

Everything on the board is editable by hand. Nothing here requires an agent, and
an agent working the board makes exactly the same changes you would.

## The tabs

A card's **stage** decides which tab it lives in. Stage is independent of the
column a card sits in.

**Backlog** — real work you have not committed to. One manually ordered list,
new cards appended to the bottom. It opens read-only: press **Edit** to reveal
checkboxes, then **Select all**, **Clear**, **Activate →** (move the ticked
cards onto the Board) or **Delete**.

**Board** — what is in play. Three columns, described below.

**Archive** — retired cards, most recently changed first, as a plain list.

Four more tabs sit beside those three, and none of them holds cards.

**Search** finds cards and epics by text and shows the matches as a list. It
takes no filter: it is the one view whose job is to find a card the board is not
showing.

**Skills** lists every skill a session can load, which agents hold each one, and
takes the address of a new one. A skill opens into a view of its own — its text,
its files, its source and a tick box per agent — and that is where a skill is
attached to an agent. The row of controls under the list narrows the list
instead: by text, by whether a skill came with Bristol or was downloaded, and by
which agent holds it. Pasting an address fetches that skill into quarantine and
files a card for `chief_of_staff` to read and judge it, because that judgment is
a read and an application cannot read. [skills.md](skills.md) is the whole of
it.

**Agents** lists the agents this installation configures, and creates or edits
any of them through a form holding everything an agent is, charter included, so
an agent can be made and corrected with no AI and no text editor.
[agents.md](agents.md) §Without an AI, and without a text editor describes the
form field by field.

**Settings** holds every choice this installation makes, the agent your next
session runs as included.

## The three columns

Only Board-stage cards have a meaningful column. A card's **status** is its
column:

- **To Do** — queued and intended for the current push.
- **Doing** — partway through. For an agent this is literal: reading into a
  ticket and commenting on it puts it in Doing, before the work starts.
- **Done** — finished. The card records when it closed.

Drag a card to reorder it within a column or move it across. Position matters:
the top of To Do is what an agent picks up next, and dragging is how you decide
that.

Above the columns sits one control row holding what applies to the Board:
**Filter**, whatever it is currently set to, and **Clear Done** at the far end.
Each column carries its own header — its name and how many cards are in it, and
nothing else, so the three read across one line.

**Refresh** and **Create** sit together at the right of the header bar, above
the tabs, because each acts on every tab rather than on the Board alone.

## Filter

**Filter** opens a panel of two facets. **Assignee** lists every owner the board
holds, `user` first. **Epic** lists every epic in play, plus **No epic** for the
cards carrying none. Each row is a tick box and the number of board cards it
matches; ticking one applies it at once, and the panel stays open.

Options within a facet add up and the two facets narrow each other: ticking two
agents shows both agents' cards, and adding an epic cuts that down to their
cards in it. A count already knows what the other facet holds, so a row reading
0 is a row worth not clicking.

What you have set shows on the control row as a chip — click its ✕ to drop that
one — and the button carries the count and the accent, so a board showing four
cards of forty never reads as a board with four cards on it. **Clear** drops
everything.

One filter narrows the Board, the Backlog and the Archive together. Nothing is
stored: a fresh launch opens on the whole board.

## A card

Click any card to load it into the detail pane on the right, where its
placement is edited in place: status, stage, owner, epic, effort and pressure
are live controls, and a change lands the moment it is made. The pane's
collapse control puts it away — the columns take the reclaimed width — and the
strip at the window's edge brings it back; its width and collapsed state
survive a restart. Double-click a card, or press **Create**, to open the
dialog, which is where a record is created and where its title, description
and record type are rewritten.

A card leads with its title, followed by the first line of its description in a
lighter face. Everything else sits in one footer row: the id, the owner and the
pressure reading on the left, then the effort, the record type and the epic as
soft-tinted pills. Pressure is drawn in the same quiet treatment as the rest —
it sorts nothing and gates nothing, so nothing on the card ramps it from green
to red.

| Field | What it holds |
| --- | --- |
| **Title** | Required. One outcome per card. |
| **Record Type** | Build or Fix. Picking one pre-fills the description with that skeleton: a Build is a story plus acceptance criteria, a Fix is expected versus observed. |
| **Description** | The body. Yours to write however you like. |
| **Stage** | Backlog, active or archive — the tab. A new card opens on the stage of the tab you pressed Create on, and on active from anywhere else, so the backlog is somewhere you choose rather than somewhere cards land. |
| **Status** | To Do, Doing or Done — the column. |
| **Owner** | Who the card belongs to: `user` or an agent slug. An agent works only its own cards. |
| **Originator** | Who raised it. |
| **Epic** | Optional grouping. Only active epics are offered, so finished work stops collecting new cards. |
| **Pressure** | 0–100. How hard the card is pushing — urgency, impact and live interest in one number, for a human eye. It sorts nothing and gates nothing. |
| **Effort** | S, M, L or XL, measuring how much of a full usage allowance the card would consume. S is under a tenth, M a tenth to about half, L half or more, XL more than one — an XL is a card to split rather than start. |

Pressure and order are deliberately separate. Order alone decides what gets
worked next; pressure is a reading you can disagree with, and a low card
carrying high pressure is a question worth asking.

## Links

Above the log, on both the detail pane and the dialog, a card shows its links,
one per row. **Add link** offers two kinds.

**Links to other cards** render as `#153 — Title`; clicking one retargets the
detail pane at that card. A link is stored once and is bidirectional by
construction: it appears on both cards, and removing it clears both ends. Three
relations:

- **related** — they belong together.
- **blocks** / **blocked by** — a dependency. The card it blocks may not start
  until this one is Done. This is the only mechanism that names *which* card is
  in the way: there is no blocked flag holding an id to set and forget, and the
  status readouts resolve a blocker live so a dependency that has been satisfied
  stops showing.

Once a blocking card is Done, **Carried summaries** appears on the card it held
up, under Links: each finished blocker's own last comment, oldest close first,
so picking the card up starts with what was decided rather than a trip through
another card's log. The status readouts print the same thing for the cards in
your queue. It is a reading of the link and that comment, not a copy — editing
the comment on the blocking card changes what the blocked one shows, and a
blocker that finished without saying anything adds nothing.

**Blocked**, on both editing surfaces, says what *kind* of thing has stopped a
card: a **dependency** (which one is the link's job), a **decision** that is
yours to make, a **capability** the agent was never granted, or something
**transient** that failed once. The reason is a value on the card; the prose that
goes with it — which tool, which call, which choice — is a comment under the Log.
A card left on a decision or a capability is listed under NEEDS YOU when a
session reads the board, since no agent can clear either by working. Moving a
card to Done clears its reason.

**Links to an address** hold a web URL, a `zotero://` citation, an
`obsidian://` note, a filesystem path, or any other scheme, with an optional
caption. Clicking hands the string to macOS, which routes it to whichever app
owns it. Bristol Tickets itself knows nothing about the schemes.

Links added while a card is still being created show as "on save" and are
written once the card exists.

Links are where a card's provenance goes — the report it came from, the note
that prompted it, the card it grew out of — rather than a sentence in the
description.

## Images

Attach an image from either the dialog or the detail pane.
Files are copied into an images folder beside the database and shown as inline
thumbnails; click one to see it full size. The database stores only the
filename, so nothing about your folder layout ends up in it. Removing an
attachment moves the file to a trash folder rather than destroying it.

## The log

Every card has a log — a timeline, newest first, with two checkboxes, both on
by default.

**Comments** are what you and the agents write: post a note with the composer
at the foot of the pane. Each shows its author and how long ago it landed.
This is where findings, decisions and what is needed next belong.

**Changes** are written by the database itself, one muted line per changed
field, with the field, its new value, who did it and when. A drag, a Clear
Done sweep, a pane edit, a dialog edit and an agent's command are all recorded
identically, so nobody has to narrate a change. Titles and descriptions record
only that they changed, never the text.

## Clear Done

**Clear Done**, at the right of the Board's control row, sweeps every card in
the Done column into the Archive in one click and writes a report.

Clearing Done is the only natural period boundary a board has, so it is where
the reporting cadence comes from. The report is one Markdown note per sweep,
written into your notebook, plus an index that trends each report against the
ones before it — cycle time, flow efficiency, work-item age, computed from the
change log. The metrics cover moves made since the log existed; it cannot be
reconstructed backwards.

The report is advisory. The sweep commits first, and a missing or unreachable
notebook folder skips the report rather than failing the sweep. If you set no
notebook, Clear Done simply archives.

## Settings

**The next session starts as** — the agent your next session runs as. It is the
one choice here that changes what the whole application means: a session as the
librarian and a session as the career coach read different files and own
different work. Pick the agent, then Save, as with everything else on the page.

**Cross-agent stage** — when one agent files a card for another, where it lands:
the Board, where the other agent will see it in its queue, or the Backlog. The
command-line writer reads the same setting, so both surfaces agree.

**Colour scheme** — a warm orange or a cool neutral appearance, each either
following your system's light/dark setting or pinned to one of the two. The
board redraws as you pick, so you can compare; Save is what keeps it.

Settings are stored in your configuration file, the same one the setup wizard
fills in. Saving round-trips the whole file, so a key this build does not
recognise survives untouched.
