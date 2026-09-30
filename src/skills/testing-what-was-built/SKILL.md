---
name: testing-what-was-built
description: Runs a skill, a Bristol feature or a finished card against what it claims, on test copies in a sandbox, records what appeared at every step, and files each defect as a card. Use when something built should be tried before it touches real data, or when a finished card's claims should be tested by someone who did not build it.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3, and a folder granted to the testing agent for its sandbox.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/config_tools/data_paths.py src/tools/ticket_tools/ticket_write.py
---
# testing-what-was-built

Input: the thing under test — an installed skill, a Bristol feature, or a card
someone closed — and what it claims. Operation: the pass below, in a sandbox.
Output: one comment giving each claim as met or not met with what appeared, and
a card for each defect.

Reading a finished card against its criteria without running anything is
`src/skills/reviewing-finished-work/SKILL.md`; this runs the thing.

## The sandbox

- **Every run happens in a folder of its own inside the testing agent's granted
  QA folder** — `runs/<subject>-<date>` under it, resolved through
  `src/tools/config_tools/data_paths.py`. The user's notebook, library, board
  data and every other folder stay out of reach of whatever runs.
- **Point the subject at the sandbox before it runs.** A skill's scripts take
  their target from an environment variable, an argument or a config key; set
  each one to the run folder first, and read the script to find them all.
- **Where the user gives a folder to test in, that folder is the sandbox**, and
  it is used as he left it. Otherwise the run builds the few files it needs
  inside its own run folder.
- **Delete the run folder when the pass is filed.** What the run showed is in
  the comment; the folder is an intermediate. A folder the user gave is his, and
  stays.

## The pass

1. **Collect the claims.** A skill's description and body, a card's acceptance
   criteria, a README's statements. Each claim becomes one expected result,
   written down before anything runs.
2. **Reconnoitre before acting.** List what the subject carries. Run each script
   with `--help` before running it for real, and read what it writes and where.
   A write outside the sandbox that the script would make is the first finding,
   and the run stops there.
3. **Snapshot the sandbox, act, snapshot again.** One action per step. After
   each, record the command, its output and exit status, and every file created,
   changed or removed between the two snapshots. A write nobody mentioned is the
   most valuable finding a pass can make.
4. **Run it end to end.** A claim is met when the thing did it, start to finish,
   on the sandbox data. A stub, a placeholder, a message saying it worked, or a
   step skipped because it looked fine is a claim not met.
5. **Run it again as the least forgiving user.** Existing files where it expects
   none, a notebook already full, wrong input, the second run of a first-run
   setup. Record what breaks.
6. **Filter before filing.** Keep a finding a real user would hit, a risk to
   data, or a claim not met. Drop what only the hostile persona would mind.
7. **File it**, per §Where findings go.

## Rating a finding

- **Severity**: critical (loses or corrupts data, or writes outside where it
  says), high (a claim not met), medium (met with friction a user would hit),
  low (cosmetic or wording).
- **Kind**: data safety, function, instructions (the body tells a session to do
  something wrong or unsafe), content, usability.

## Where findings go

- **One comment on the card the test answers**, giving each claim as met or not
  met, the step that showed it and what appeared. A test with no card behind it
  gets a card of its own first, assigned to the testing agent.
- **Each defect is a Fix card** — Expected, Observed — assigned to the agent
  that built the thing, with the testing agent as reporter and a link to the
  card tested. A defect in an installed third-party skill goes to
  `chief_of_staff`, which decides whether it stays.
- **At most ten defect cards a pass, worst first.** The rest are lines in the
  comment.
- **Nothing found is a result**, and it is still the comment.
- **The tester fixes nothing.** A fix made by the tester is untested work with
  no author.

## Where this came from

- **Hermes' dogfood skill**: a written plan before exploring, evidence for every
  finding, severity and category on each, and its rule that the silent failure
  is the valuable one. Its browser console check is step 3's before-and-after
  snapshot here, because what goes wrong silently in a skill is a file.
- **Hermes' adversarial-ux-test**: the worst-case user pass, its mandatory
  filter before anything is filed, and its cap on tickets per session.
- **The Claude Code verification agents** (task-completion and reality-check
  agents in the community collections): claimed completion is tested end to
  end, and a stub is a failure.
- **Anthropic's webapp-testing skill**: reconnaissance before action, and
  running a bundled script with `--help` before reading or running it.
- **Claude Code's subagent guidance**: one responsibility and the narrowest
  tools. Here that is the sandbox folder grant and the rule that the tester
  fixes nothing.
- **Not taken**: coverage and automation percentages and progress-report
  templates from the generic QA agent definitions, which measure a test
  programme rather than find a defect.

## Failure modes

- **A run touched a real folder** → the sandbox step was skipped. Stop, say what
  was written where, and file it as critical against the testing pass itself.
- **A claim passed because the output said success** → step 4.
- **A defect in a comment and nowhere else** → it will not be worked.
