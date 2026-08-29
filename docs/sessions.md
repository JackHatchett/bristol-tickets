# Sessions

A session is one conversation with an agent host, pointed at this folder,
running as one agent, working one board. The loop is short:

1. **Pick the agent** on the board's Settings tab, under **Agent Sessions** —
   *Agent* — and Save.
2. **Open a session** in your agent host with the `bristol_tickets` folder
   selected.
3. **Say what you want.**
4. **Watch the board.** Cards move as the work happens.

## What happens when a session starts

You do not have to prompt any of this. The agent reads `src/app.md`, which tells
it how to boot: read the configuration one key at a time, find out which agent is
active, load that agent's charter, list the skills it can reach, then read the
board and work out what it should be doing.

Listing the skills costs one line each — a name and the sentence saying when it
applies. The instructions inside a skill are read only when a task matches that
sentence, and the agent says which skill it opened. Installing one is therefore
enough to change what a session does; you do not have to mention it.

The last step prints a snapshot: the current milestone, the active epics, and
the agent's own queue in order, with the next action named at the top. The
chief of staff also sees a fleet section — the cards other agents own — as
context, never as its own work.

## What "continue" means

Say **continue** and the agent starts at the top of its queue. How far it goes
is Settings → **Agent Sessions** → *Work Scope*: *Whole Queue*, the default, works down
through every card without asking permission between them; *One Ticket* works
the next action and stops there. On *Whole Queue* it stops when the
queue is empty or when one of a short list of things happens: it needs a
decision only you can make, it needs a credential or a permission it has not
been granted, it is grinding on something that keeps failing, or the
conversation is running out of room.

Anything else you say, it responds to. If nothing you said was actionable, it
names the next action and asks whether to start.

When a session ends having written files inside a git repository, whatever
stopped it, the last thing in its message is a block you can paste into a
terminal to commit that work. It never runs the commit itself. Turn this off in
Settings → **Agent Sessions** → *Git Commit on Session Close*.

## How the agent decides what is next

Ordering is entirely the board's, and you own it by dragging cards.

- Cards in **Doing** come before cards in **To Do**, in board order.
- Only if both are empty does the agent look at its **Backlog**, and then only
  to raise it with you. A backlog card is a planning signal, never something it
  starts on its own.
- An agent owns a card when the card is assigned to it, or when the card is
  unassigned and its epic names it as owner.
- A card blocked by something that is not Done is passed over, and the agent
  takes the next card in order. It comes back to the passed-over card, in the
  same place, once every card blocking it is Done. A blocker never moves a card
  up or down the queue, and the agent never works the unblocked half of one in
  passing.

Nothing else moves a card up or down that list — not pressure, not a comment,
not how big the card looks. If you want something done first, drag it to the
top.

## What an agent does to the board

Touching a card puts it in **Doing** immediately, before the work starts:
reading into it, commenting on it, linking it, part-executing it. The only cards
left in To Do at the end of a session are the ones nobody touched.

When the work finishes, the card goes to **Done** with a comment saying what
changed. When it cannot finish this session, the card stays in Doing at the top
of its column with a comment about where it got to — that card *is* the handoff,
and the next session picks it up from there.

Work an agent cannot finish, or that a different agent should own, becomes a
card and nothing else. There is no note left in a folder, no message relayed
through you, no status file to check. If you find yourself copying text from one
session into another, something has gone wrong: agents hand work to each other
by assigning a card.

## Working alongside it

The board is not read-only while a session runs. Drag a card, write a comment,
change a description, retire something — whichever surface acts, the other sees
it on its next read. **Refresh**, in the header bar, picks up changes an agent
made while the window was open, whichever tab you are on.

The rules above bind the agents, not you. Chat is how you talk to your agent and
it does not need to be a card first: ask, think out loud, change your mind, correct
it. An agent will not tell you to file a ticket for something it could simply
do.

## Running one agent per session

Sessions are per agent on purpose — "do the chief_of_staff cards," then later
"do the career_coach cards." A session loads only that agent's charter and
playbooks rather than the whole library, which is why the assignee on a card
matters: it is the routing key.

To pin a project to a specific agent regardless of the board's setting, put
`agent_override: <slug>` in that project's instructions. It applies to that
project's sessions only and never writes back to your configuration. A host that
offers no per-project instructions cannot pin one; on that host the board's
setting is the only answer, and reading `src/app.md` is a line you type.

*The next session starts as* means the next session. A session resolves its
identity once, when it opens, so changing the setting to launch a second session
as a different agent leaves the first one as the agent it started as. Both run
against the same board.
