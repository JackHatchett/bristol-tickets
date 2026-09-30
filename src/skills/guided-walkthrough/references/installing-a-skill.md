# Installing a skill somebody else wrote

The feature: taking a skill published by a stranger and ending with it loadable
and attached to an agent. The user's part is three moves — find the skill in a
browser, import its address in the Skills tab, and attach it to an agent. The
survey of hubs, licences and the risk figures is `docs/skills.md`; the loader's
own contract is `src/tools/skill_tools/README.md`. This file is the run.

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

**Where the skill is the whole repository** — its `SKILL.md` at the top level,
beside the `LICENSE` — the repository's own address is the skill's address, and
the `SKILL.md` file's `blob` address installs it too.

**Divergence:** a list such as awesome-hermes-skills links each entry to its
repository rather than to the skill's folder. Where that repository holds
several skills, its top level has no `SKILL.md`, and the install says so and
asks for the skill's own folder; the user clicks through to the one wanted.

## Step 2 — Import

**The user does:** pastes the address into the Skills tab in Bristol Tickets
and presses Import.

**What appears:** "Fetching…", then one of two results.

- **The skill is in the list and ready to use.** The line under the address
  box gives its name, where it was downloaded from with the commit, what it
  carries, and what the scan found. The new row is selected in the list.
- **"Not imported"**, with each scan finding by severity, file and line, or a
  line saying the scanner is not installed and the command that installs it.
  Nothing was added.

**What it means:** the scan runs before anything is added, so a skill in the
list is one the scan passed. A row saying some code was not scanned names code
in a language the scanner does not read.

**Divergence:** a repository holding several skills has no `SKILL.md` at its
top level, and the import says so and asks for the skill's own folder.

## Step 3 — Opening it

**The user does:** double-clicks the new row.

**What appears:** its view: the description, where it came from with a button
to the source at that commit, what it carries and what the scan found, a tick
box per agent, its files, and its `SKILL.md`.

**What it means:** everything a session will read when the skill matches a
task is on this page.

## Step 4 — Attaching it

**The user does:** ticks the agent whose work the skill serves.

**What appears:** the row's last fact changes to "Held by" that agent.

**What it means:** attachment is order, not permission. Any agent can reach any
skill; attaching decides which set a session matches first.

**The step that proves it:** open a session as that agent, give it a task the
skill's description covers, and have it say which skill it loaded. A skill that
never gets loaded has been installed and not adopted.

## What the user should be able to do afterwards

Find a skill, tell from its description and its files whether it is worth
having, import it, say what the scan checked and what it did not, and attach it
to the agent whose work it serves.
