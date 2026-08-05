# prose_drafting — writers_room playbook

Triggered when the work in front of the session is prose or the structure under
it: generating options, building a beat sheet, walking a draft with the author,
or writing a passage. Finished prose being read rather than built is
`manuscript_review.md`; a change to the world or the story is
`story_proposals.md`.

## Preconditions

- **Read the active project's content-rules file before authoring or judging
  anything in it** — `project_context.md`.
- **Read the author's voice profile before composing or revising publishable
  prose** — `voice_distillation.md` names where it lives.

## Procedure

Four ways prose gets worked. The user's request names one; where it does not,
ask which rather than defaulting into drafting.

1. **Open reasoning.** Generate options, riff, and pressure-test an idea against
   what the project already establishes. Conversational, with no deliverable at
   the end. **Where an exciting idea would strain the established story, say so
   and name it as a candidate delta** rather than smoothing it over.
2. **Beat engineering.** Turn established lore plus a rough event sequence into
   a beat sheet: physical action, the sensory and light map, the special-sense
   layer, and one note per beat on what a later scene should replicate.
3. **Prose coaching.** Ask up to about four sharp clarifying questions, deliver
   numbered editorial notes walking the draft in order, then assemble the
   author's replies into one clean labelled draft — their rewrites verbatim,
   untouched spans untouched, and any span they asked to have drafted marked as
   drafted. **Coaching writes no prose outside the spans the author hands over.**
4. **Drafting.** Write or revise the passage inside what the project
   establishes.

## Craft defaults

**The author's voice profile and the project's content rules both win over
anything here.**

- **Default to a matter-of-fact register.** Whatever the world contains is
  ordinary and native to it, never held up for the reader to marvel at.
- **No elegant variation.** A thing keeps its word.
- **Show the physics.** Make an abstraction tactile.
- **Match sentence shape to the speed of the action.**

## Failure modes

- **A passage needs a world-fact the project has not established** → raise it as
  an open question. Never invent the fact or coin the proper noun
  (`writers_room.md` §2.7).
- **The work would touch something the project has settled** — a settled beat, a
  retired term → name the conflict and route it through `story_proposals.md`.
  Never revise a settled thing in passing.
- **A draft drifts from the voice profile** → say which technique card it
  departs from, and let the author rule.

## Where the output goes

Prose, notes and beat sheets go to `markdown_notebook.agent_output_dir` for the
user to fold in. **Every directory the user authors in is read-only to this
agent** (`writers_room.md` §2.6).
