# The board

Bristol Tickets is the desktop app: a Kanban board over one SQLite database. Run
it with `python3 src/tools/bristol/app.py`, or from the Dock if you built a
launcher.

Everything on the board is editable by hand. Nothing here requires an agent, and
an agent working the board makes exactly the same changes you would.

## Above the tabs: Start next session as

A strip across the top of every screen names the agent your next Claude session
will run as. It sits outside the tabs because it changes what the whole
application means — a session as the librarian and a session as the career coach
read different files and own different work. Choosing an agent writes that one
choice to your configuration and nothing else.

## The three tabs

A card's **stage** decides which tab it lives in. Stage is independent of the
column a card sits in.

**Backlog** — real work you have not committed to. One manually ordered list,
new cards appended to the bottom. It opens read-only: press **Edit** to reveal
checkboxes, then **Select all**, **Clear**, **Activate →** (move the ticked
cards onto the Board) or **Delete**.

**Board** — what is in play. Three columns, described below.

**Archive** — retired cards, most recently changed first, as a plain list.

**Search** finds cards and epics by text and shows the matches as a list.
**Settings** holds choices about how the board behaves.

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

Above the columns sits one control row holding what applies to the whole board:
the epic filter and **Refresh**. Each column carries its own header — its name,
how many cards are in it, and an overflow menu holding what acts on that column
alone: creating a card in it, and, on Done, **Clear Done**.

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
| **Stage** | Backlog, active or archive — the tab. |
| **Status** | To Do, Doing or Done — the column. |
| **Owner** | Who the card belongs to: `user` or an agent slug. An agent works only its own cards. |
| **Originator** | Who raised it. |
| **Epic** | Optional grouping. Only active epics are offered, so finished work stops collecting new cards. |
| **Pressure** | 0–100. How hard the card is pushing — urgency, impact and live interest in one number, for a human eye. It sorts nothing and gates nothing. |
| **Effort** | S, M, L or XL, measuring how much of a full Claude usage allowance the card would consume. S is under a tenth, M a tenth to about half, L half or more, XL more than one — an XL is a card to split rather than start. |

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
  until this one is Done. This is the only mechanism for "not yet": there is no
  blocked flag to set and forget, and the status readouts resolve a blocker live
  so a dependency that has been satisfied stops showing.

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

**Clear Done**, in the Done column's own menu, sweeps every card in that column
into the Archive in one click and writes a report.

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

**Cross-agent stage** — when one agent files a card for another, where it lands:
the Board, where the other agent will see it in its queue, or the Backlog. The
command-line writer reads the same setting, so both surfaces agree.

**Colour scheme** — a warm orange or a cool neutral appearance, each either
following your system's light/dark setting or pinned to one of the two. The
board redraws as you pick, so you can compare; Save is what keeps it.

Settings are stored in your configuration file, the same one the setup wizard
fills in. Saving round-trips the whole file, so a key this build does not
recognise survives untouched.
