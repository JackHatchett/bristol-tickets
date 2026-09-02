# Skills

A **skill** is a folder holding one Markdown file that tells an agent how to do
one job: how to write a cover letter, how to catalogue a game, how to close a
session. The file opens with a name and a one-line description saying when the
skill applies, and that description is the whole of what a session reads until
a task matches it.

This is why an agent gains an ability without its charter changing. The charter
says who the agent is and what stops it; the skills say what it knows how to do,
and they are listed rather than written into it.

## Where they live

Two folders, and a skill in either loads the same way.

- **The ones that came with Bristol**, under `src/skills/`. They are published
  with the code and they are the procedures this system runs on.
- **The ones you install**, under whatever folder you name at
  `skills.install_dir` in your configuration. It is never published, and it can
  be a folder of skills you already keep — point the setting at it and every
  skill inside is listed the moment a session starts, with nothing copied.

Neither folder has to exist. A missing one means no skills of that kind, not an
error.

## What a session pays for them

At the start of every session an agent reads one line per skill: its name, where
it came from, and the sentence saying when it applies. Nothing else. When a task
matches one of those sentences the agent opens that one skill and says which one
it opened.

So a hundred installed skills cost a hundred lines, once, and the length of a
skill costs nothing until it is the right skill. A skill's own scripts and
reference files are not read even then; the skill's body says when to open one.

## Attaching a skill to an agent

Attaching puts a skill first in what that agent considers. It takes nothing away
from anyone: a skill attached to no agent is available to every agent, and any
agent can still reach any skill when a task calls for it. Attachment is order,
never permission.

You attach one on the **Skills** tab by ticking the agent in the skill's own
view, or from the command line:

```bash
python3 src/tools/skill_tools/skills.py list --agent career_coach
python3 src/tools/skill_tools/skills.py attach cover-letter --agent career_coach
python3 src/tools/skill_tools/skills.py detach cover-letter --agent career_coach
```

## Installing one somebody else wrote

People publish skills free, by the thousand. Installing one is the address of
the folder you are looking at in your browser:

```bash
python3 src/tools/skill_tools/skills.py install <repo-url> <path-in-repo>
```

or the same address pasted into the **Skills** tab.

**What arrives is quarantined.** It lands in a hidden folder inside your install
root, where no session can list it or load it, and Bristol prints an inventory
of every file in it with its size, its hash, and a mark against anything that is
executable code. Nothing runs.

**Then someone reads it.** Pasting an address into the Skills tab files a card
for `chief_of_staff`, because judging a skill means reading its body and every
script it carries, and an application cannot read. A session opens the card,
reads, and either promotes the skill or leaves it in quarantine with the card
saying what stopped it. You can overrule a refusal; that part is yours.

**Promoting it is one command**, `skills.py trust <name>`, and it moves a folder
and asserts nothing. What makes it safe is the reading that came before it.

## The audit, and what it does not check

`skills.py audit <name>` prints where a skill came from, then a scan of its
Python, then the skill's own text, then every script in full.

The scanner is **bandit**, and it reads Python only. A skill's shell,
JavaScript, Ruby or PowerShell goes unread and the report names it. It does not
follow data between files, it cannot tell a dangerous call used correctly from a
safe one used wrongly, and code that is obfuscated or fetched while it runs
reads to it as ordinary Python. A finding is a place to look. A clean report
says these particular tests matched nothing, and no more.

Nothing here reviews a downloaded skill on your behalf.

## Something written for another tool

A role description written for a different assistant — a subagent definition, a
slash command, a prompt-pack entry — is one Markdown file with a header on top,
and one command turns it into a skill:

```bash
python3 src/tools/skill_tools/skills.py convert <file.md>
```

The name, the description and the licence cross. The lines that route work
inside the other tool — which model to use, which of its tools to allow — are
dropped, and the output names each one it dropped, because your AI application
decides both and Bristol has no say in either. A file that states no description
is refused rather than given one: a skill with no description never routes.

## What crosses from another tool, and what does not

The claim is narrow and worth stating plainly: **a skill crosses, and nothing
else does.** A folder with a `SKILL.md` in it loads here whoever wrote it and
whichever program they wrote it for, and you need no account with that program
and none of the tools it mentions. Many published skills were written for
Hermes; the claim about Hermes is only that those skills load. Its board, its
runtime, its scheduler and its saved profiles are its own, and Bristol claims
nothing about them. A skill that expects a password, an API key or another
program's own features does nothing here, and installing it says so and leaves
the choice to you. `README.md` §Skills other people wrote itemises it.

## Where to browse for one

Nothing in this list is reviewed by Bristol, and each entry says what reviews
it, which is usually less than it sounds.

| Where | What it holds | What reviews it |
| --- | --- | --- |
| `github.com/anthropics/skills` | The format's own template, and the skills behind one assistant's document handling | Nothing published; one vendor's repository |
| `github.com/agentskills/agentskills` | The Agent Skills standard itself, not a catalogue | Its own contribution process |
| `github.com/ZeroPointRepo/awesome-hermes-skills` | 258 entries, most of them Hermes' own | Curated by hand, and it says it is not an audit |
| `skills.sh` | The largest directory, listing skills by repository | A security-audit section with no stated process |

**Scale and trust run in opposite directions**, so the two smallest entries are
the two worth reading first.

**A licence belongs to the skill, not to the list it appears on.** Bristol
records what it finds beside a skill as it installs it — the repository, the
folder, the exact commit and the licence, read from the skill's own header, a
licence file beside it, or the repository root — and infers nothing. A source
that states no licence anywhere is recorded as saying none, which is a different
fact from a blank.

**Bristol redistributes nobody's bytes.** Hand one of your agents to someone
else and each of its skills travels as the address it came from, under that
source's own terms; the person importing fetches it themselves.

## Removing one

```bash
python3 src/tools/skill_tools/skills.py remove <name>
```

It deletes an installed or quarantined skill and detaches it from every agent
that held it. It refuses a skill that came with Bristol: those are source under
version control, and removing one is an edit to the repository.
