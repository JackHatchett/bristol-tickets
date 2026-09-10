# Installing a skill somebody else wrote

The feature: taking a skill published by a stranger and ending with it loadable
and attached to an agent. The user's part is three moves — find a folder in a
browser, hand its address to a session, read what comes back and answer the one
question it ends on. The survey of hubs, licences and the risk figures is
`docs/skills.md`; the loader's own contract is
`src/tools/skill_tools/README.md`. This file is the run.

## Before starting

- **Ask which hub the user wants to browse**, and let them browse it. Choosing
  the skill for them removes the only part of this that teaches them to judge
  one. `docs/skills.md` §Where to browse for one is the list, each with what
  reviews it in that hub's own words.
- **Say what makes one worth installing before they pick**: a licence present,
  a description saying *when* to use it rather than only what it is, and no
  dependency on another product's credentials or features.

## Step 1 — The address

**The user does:** opens the skill's own folder on the hub and copies the
address from the browser's bar.

**What appears:** an address of the form
`github.com/<owner>/<repo>/tree/<branch>/<path>`. Looking at the `SKILL.md`
file itself gives `blob` instead of `tree`, and that works too — the folder
holding the file is what installs.

**What it means:** the address carries the repository and the path inside it,
which is the whole of what the install command needs.

**Divergence:** an address with neither `/tree/` nor `/blob/` in it is the
repository's own address rather than the skill folder's. The command says so.

## Step 2 — Handing it over

**The user does:** pastes the address into the session and says to install it,
or pastes it into the Skills tab in Bristol Tickets.

**What appears, by route:** a session runs
`python3 src/tools/skill_tools/skills.py install <repo-url> <path-in-repo>`.
The tab performs the same install and files a card for `chief_of_staff`,
because judging a skill is a read of its body and every script it carries and
an application cannot read.

**What it means:** the fetch is mechanical either way, and the judgment is a
person's either way.

## Step 3 — Reading what comes back

**What appears:** five things, and each is worth naming to the user as it goes
past.

- **Where it went** — a quarantine folder that a session can neither list nor
  load from. Installing never makes a skill usable.
- **Where it came from** — the repository, the path, and the exact commit
  rather than "the latest version".
- **Its licence, and where that was read from** — the skill's own frontmatter,
  a licence file beside it, or one at the repository root. A licence is a
  property of the skill, not of the hub that listed it, and a source stating
  none anywhere is recorded as `absent`, which is a different fact from blank.
- **What it carried** — every file with its size and hash, and a mark against
  anything that is executable code.
- **What read it** — the scanner's report.

**The line to stop on:** *No scanner. bandit is not installed for this
interpreter, so nothing has read this code but you.* On a skill carrying no
code this costs nothing and the session reads the body instead. On a skill
carrying code it means the opposite, and unread is unjudged.

**Divergence:** a compatibility note appears where the skill's own frontmatter
declares something with no reader here — an environment variable it wants
credentials for, or another product's toolset it gates on. It is a statement
and not a refusal; what needs those will not run, and the rest of the body may
still be worth reading.

**Divergence:** a name already present in either root is refused rather than
overwritten, and the install takes `--name` to rename it on the way in.

## Step 4 — The one command

**The user does:** runs, from the Bristol folder,
`python3 src/tools/skill_tools/skills.py trust <name>`.

**What appears:** the skill moves out of quarantine into the folder sessions
load from.

**What it means, and say it before they type it:** from then on the skill's
description sits in every session's opening index, its body opens when a task
matches it, and any code it carries is code a session may choose to run.
Nothing runs at the moment of typing.

**This one is the user's.** Nothing here trusts a skill on their behalf, and a
session offering to is the thing this design withholds. `trust` consults no
scanner: what makes it safe is the reading that came before it.

**Divergence:** a skill that did not clear a read stays in quarantine and the
card says which of the three stopped it — a body instructing a session to edit
its own rules, code doing what the description never mentions, or code that
could not be read. Overruling a refusal is the user's and should be rare.

## Step 5 — Attaching and using it

**Ordinarily the session attaches**, straight after the user trusts. In a
walkthrough the user runs it instead, once, so they have done it:
`python3 src/tools/skill_tools/skills.py attach <name> --agent <slug>`. That is
a variation in who types, not a different fact about the feature.

**What appears:** `skills.py list --agent <slug>` marks it as one of that
agent's own and puts it first.

**What it means:** attachment is order, not permission. Any agent can reach any
loadable skill; attaching decides which set a session matches first.

**The step that proves it:** open a session as that agent, give it a task the
skill's description covers, and have it say which skill it loaded. A skill that
never gets loaded has been installed and not adopted.

## What the user should be able to do afterwards

Find a skill, tell from its description and its files whether it is worth
having, install it, say what quarantine held back and why, trust it themselves,
and attach it to the agent whose work it serves.
