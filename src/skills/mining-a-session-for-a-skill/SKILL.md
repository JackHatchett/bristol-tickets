---
name: mining-a-session-for-a-skill
description: Reads a session that has just finished and decides whether anything in it is worth keeping as a skill - a new one, a patch to one that exists, or nothing - then drafts what it found. Use when someone says to capture this session as a skill, to see whether a session taught anything reusable, or after a long build or research session whose method would otherwise have to be worked out again.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3 to read the board and the skill loader.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/skill_tools/skills.py src/tools/skill_tools/propose_skill.py
---
# mining-a-session-for-a-skill

Input: a session that has finished doing something. Operation: judge whether its
method is worth keeping, and at what size. Output: a new skill, a patch to an
existing one, or a stated finding that there is nothing. The skill format and
folder shape are `src/skills/skill-conversion/SKILL.md`; the authoring mechanics
for a new skill — drafting, test prompts, description tuning — are the installed
`skill-creator`, loaded with `python3 src/tools/skill_tools/skills.py view
skill-creator`.

## Precedence against session-review

`src/skills/session-review/SKILL.md` is the light pass: it runs at the close of
any session that changed something, reads the board alone, and proposes at most
one patch. This is the heavy pass: it runs on request, reads the session itself,
and may conclude that a whole new skill exists.

- **Where both would fire, this one runs and session-review does not.** A
  session already mined has had its one proposal.
- **Neither pass runs twice on one session.**

## The corpus

Everything the session did, and the session's own record of doing it: the
commands run and what they returned, the files written and their diffs, the
research read, the corrections the user made, and the board cards the session
moved with their comments.

- **The corpus is the session running this pass, and nothing else.** Never a
  past conversation, a conversation search, a stored memory, or any record that
  outlives a session. The permission this skill holds is to look at what the
  session in front of it just did, and it reaches no further whatever a host
  makes available.

- **This pass may read the session's own conversation, and session-review may
  not.** A method is not work state, so `src/app.md` §The board is the only
  channel does not reach it; that section governs next actions, ordering and
  in-progress facts, all of which stay on the board here as everywhere.
- **Nothing read here becomes a record of what happened.** Only a method that
  holds for a class of task leaves this pass, which is why §What is worth
  keeping tests for one; a skill stating what a session did would be the
  history the board already owns.
- **Carry the evidence into the output.** A transcript is gone once the session
  closes, so a proposal states the command line, the sequence or the correction
  in full rather than citing where it was seen. What a later reader cannot check
  in the proposal itself is not in the proposal.

## What is worth keeping

A candidate has to pass all four.

- **It would be re-derived.** A later session facing the same class of task
  would spend real effort working it out again.
- **It describes a class, not this task.** `querying a paginated public API`
  survives; `fetching one account's posts from one service` does not. A name
  that only makes sense for one card, error string or feature is the signal
  that a session narrative is being minted as a skill.
- **It is a method, not a decision.** What the user chose belongs to the card
  that carried the choice. How the work was done belongs to a skill.
- **It holds when the environment changes.** A missing binary, an unmounted
  volume, an ungranted permission and an unconfigured credential are all things
  the user can change; a rule written from one of them outlives its cause and
  gets cited for months. `src/skills/session-review/SKILL.md` §What is never a
  lesson owns this list in full and applies here unchanged.

## The three verdicts

**Nothing.** The real outcome most of the time, and it is stated rather than
padded into a thin skill. Say what was considered and why it failed the tests.

**A patch.** The method belongs inside a skill that already covers the
territory. Hand it to `src/skills/session-review/SKILL.md` §Procedure, which
owns the patch route and the card it files.

**A new skill.** Everything below.

## Procedure for a new skill

### Step 1 — Name the class and check it is not already held

```
python3 src/tools/skill_tools/skills.py list
```

Read the descriptions of anything adjacent. A candidate whose territory an
existing skill already covers is a patch, and goes back to §The three verdicts.

### Step 2 — Write the body from what the session actually did

The shape is `src/skills/skill-conversion/SKILL.md` — frontmatter, then
Preconditions, Procedure, Failure modes, Audit — under the style contract in
`src/templates/identity_template.md` §The governing-doc style contract.

- **Every step traces to something the session ran or read.** A step nobody
  performed is a guess about a procedure, and this pass has a session precisely
  so it need not guess.
- **Generalize each step to the class as you write it.** The session's file
  names, paths and account handles are the example, never the instruction.
- **A failure mode is one the session actually hit**, with what resolved it.
  A dead end the session never got out of is not a failure mode; it is an open
  question, and it goes to the user or onto a card.

### Step 3 — Decide who may write it

`src/app.md` §Content is yours; behavior is chief_of_staff's decides this, and
it turns only on which agent is running.

- **chief_of_staff writes the skill folder** and attaches it —
  `skills.py attach <name> --agent <slug>`.
- **Every other agent files the draft as a card** and stops:

```
python3 src/tools/skill_tools/propose_skill.py \
  --skill <name> --reporter <your slug> \
  --change "<what the skill would do>" --body-file <the drafted SKILL.md> \
  --attach-to <the agent it would serve>
```

### Step 4 — Say what was rejected

Report the verdict with the candidates that lost and the test each one failed.
A pass that reports only its winner cannot be argued with.

## Failure modes

- **A skill named after the session's task** → §What is worth keeping, test two.
  Drop it or raise it to the class.
- **A proposal citing the transcript instead of quoting it** → the evidence dies
  with the session. §The corpus requires the text itself.
- **Three skills out of one session** → the pass has stopped judging. One
  session yields at most one new skill; a second candidate that genuinely
  survives all four tests becomes a card describing it, not a second folder.
- **A skill written from an unresolved failure** → a sequence of dead ends
  presented as guidance. It is an open question until something resolved it.
- **Both this pass and session-review filing on one session** → §Precedence
  against session-review.

## Audit

- Every skill this pass produced carries a name that reads as a class of task
  rather than an instance of one.
- No skill this pass produced contains a path, handle or filename that belongs to
  one installation, except as a labelled example.
- No session carries both a proposal from this pass and one from session-review.
- No agent but chief_of_staff wrote a file under `src/skills/`.
