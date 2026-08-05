# Bristol

A Kanban board that runs on your desktop, and a set of AI agents that work it.

You keep your work on a board of cards: to-do, doing, done. The difference from
every other board is who picks the cards up. Open a Claude session pointed at
this folder, say "continue," and the agent reads the board, takes the top card
in its queue, does the work on your actual files, and writes back what it did.
Next time you open the board, the card has moved.

Bristol Tickets is the desktop app — a Kanban board over a single SQLite
database. The agents are Markdown files describing seven roles: a chief of staff
who maintains the system, a career coach, a librarian, a teaching assistant, a
fiction writer, a game-design coach, and a client-services agent. You choose
which ones you want when you install it.

## What it needs

A Claude subscription that includes Cowork, the Claude desktop app, Python 3.10
or later, and macOS. Without Cowork there is no agent — you get a working Kanban
board and nothing else. [install.md](install.md) covers the whole chain.

## What it is not

It is not a hosted service, a team tool, or a task manager with an AI feature
bolted on. Everything lives in files on your machine: one SQLite database, one
JSON config, a folder of Markdown. Nothing is sent anywhere except what you say
to Claude in a session.

## The manual

- **[install.md](install.md)** — the prerequisites, in the order they have to
  happen, and what the first run asks you.
- **[sessions.md](sessions.md)** — the loop you actually live in: pick an agent,
  open Cowork, say what you want.
- **[board.md](board.md)** — the board as a product. Tabs, columns, cards,
  links, images, comments, search, Clear Done, reports.
- **[agents.md](agents.md)** — the seven shipped agents: what each is for, what
  it can do, what it needs configured.
- **[configuration.md](configuration.md)** — every configuration key, its
  default, and whether you need it.
- **[architecture.md](architecture.md)** — how the app, the database and the
  agent files fit together.
