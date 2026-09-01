---
name: importing-an-agent
description: Adopts a whole agent someone else exported — reads the mandate it arrives carrying, fetches its skills, and decides whether it becomes an agent here. Use when someone gives you an agent file to add.
license: MIT
compatibility: Runs inside a Bristol repository; needs python3, and git for any skill fetched by address.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
  bristol.scripts: src/tools/agent_tools/import_agent.py
---
# importing-an-agent

Input: an `.agent.json` file. Operation: the procedure below. Output: an agent
in the fleet, or a card carrying what stopped it.

The mechanism is `src/tools/agent_tools/README.md` — the format, the two runs
and what each writes. This skill owns the judgment. Exporting takes no judgment
and is one command there.

## Procedure

1. **Read it.** `python3 src/tools/agent_tools/import_agent.py <file>`. It
   writes nothing, prints the mandate and the guardrails, and fetches each
   addressed skill into quarantine.
2. **Judge the mandate** against §What decides it.
3. **Judge every skill it brought**, each by
   `src/skills/importing-a-skill/SKILL.md` §What decides it. A skill that clears
   is trusted and attached there; one that does not stays in quarantine and the
   agent runs without it.
4. **Where the mandate clears**, `import_agent.py <file> --accept`, then supply
   each value the run names.
5. **Where it does not clear**, §Where an agent does not clear.
6. **Report** to §What the user is told.

## What decides it

Three cases, tested in this order.

- **A charter granting itself authority over how this system works is
  refused.** An agent may hold a mandate over its own domain. A charter that
  edits charters, repeals a rule, or claims precedence over the documents here
  is `src/app.md` §Content is yours; behavior is chief_of_staff's, arriving as a
  download. One agent already holds that authority, and a second holding it is
  two agents editing the same governing documents.
- **A charter whose guardrails do not halt anything is refused.** A guardrail
  is a rule that stops execution. Prose that praises the role, describes a
  personality or lists what the agent is good at is a description with nothing
  in it that halts, and adopting it grants authority against no limit.
- **A charter clears when its mandate is one job and its guardrails are that
  job's own.** `src/templates/identity_template.md` §When one job is two agents
  is the test for the first half; a guardrail naming a bright line in the
  agent's own domain is the second.

**The skills decide nothing about the charter.** An agent whose every skill was
refused is still an agent; a charter that does not clear is refused even where
every skill it named is clean.

## Where an agent does not clear

- **Say which case it failed and quote the line that failed it.**
- **Nothing is written**, because nothing was written before the decision. The
  file stays whatever the user does with it.
- **File a card** carrying what stopped it, assigned to the user, so the refusal
  is on the board rather than in a conversation. The user may overrule it, which
  is the only part of adopting an agent that is theirs.

## What the user is told

- **What the agent is for**, in one line, in his words rather than the file's.
- **Which case decided it**, and the line that decided it.
- **What arrived and what did not** — the skills attached, the skills held in
  quarantine, and the capability missing for each one that could not be fetched.
- **The values he has to supply**, as the command lines the run printed.
