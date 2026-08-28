# The agents

Seven agents ship with Bristol. An agent is three things: an entry in your
configuration, holding its paths and settings; a charter, a Markdown file under
`src/agent_identities/` that it reads in full at the start of every session,
holding who it is, what it is for and what it may not do; and skills, folders of
instructions it opens only when a task calls for one. Which of the three holds a
given fact follows from what a session does with the fact — look it up, hold it
throughout, or open it when the work needs it — rather than from what the fact
is about. That shape is written down in `src/templates/identity_template.md`
§What an agent is made of.

One agent is active at a time. You choose it on the board's Settings tab, and
the session that starts next loads that agent's charter and works that
agent's cards. An agent never picks up a card belonging to another; when it
needs one of them to do something, it files a card assigned to them.

Every agent shares the same shape: reusable machinery under `src/`, and your
personal content under `data/<instance>/`, which is never published. That split
is what lets you fork the repository without leaking anything.

You pick which agents exist when you install. An agent you did not enable has no
folders and no presence on the board.

---

## chief_of_staff

**For** maintaining Bristol itself.

It is the lead developer and operator of the system: it restructures folders,
edits configuration, writes and fixes the tools, and keeps the file environment
organised. It is the only agent permitted to change how any agent works —
charters, playbooks, protocols, tools. Every other agent adds content; behaviour
changes route here as a card.

It is also the agent to talk to about your own machine. Organising a folder,
auditing storage, deduplicating photos, migrating an old setup — the file
management and maintenance tools under `src/tools/` are its territory.

**Needs** nothing beyond a working install.

---

## career_coach

**For** a job search, in any field and at any seniority.

It triages job descriptions against your history, tailors a resume to a specific
posting, drafts cover letters in a voice distilled from writing you have already
done, builds interview-prep material, and tracks applications in a local
database. An optional pipeline harvests job alerts out of your email on a
schedule.

**Needs** a `data/<instance>/career/` folder holding your resume, employment
history, voice samples and context files. The agent builds this up with you over
the first few sessions rather than requiring it up front. Email harvesting and
job-description scraping need the optional tools from
[install.md](install.md) §3.

---

## librarian

**For** the collections you keep and consult.

Two domains ship with it, both optional. A **book library** catalogued in
Zotero: it reads your library, builds reading lists, and writes reading-list
notes into your notebook. A **recipe collection**: a folder of Markdown recipes
it normalises to one consistent format. A collection of your own — records,
film, tools, seeds, board games — is the same job, and the charter points at it
without modification.

**Needs** Zotero installed for the book domain, and a notebook folder for the
recipe domain. An installation with neither still has a working fleet; the agent
simply has nothing to curate yet.

---

## teaching_assistant

**For** teaching yourself something.

It builds and maintains a course: a syllabus, a sequence of lessons, exercises,
quizzes, and a progress record you can navigate across several courses at once.
The pipeline is subject-independent — a programming language, a branch of
mathematics, a trade skill, a spoken language. It renders any lesson to a
readable HTML page. It is the sole author of coursework; no other agent writes
into a course.

**Needs** a Markdown notebook, where courses live as one folder each. Its
lesson-production stages can optionally be routed to an external AI tool; left
alone, it does every stage itself.

---

## writers_room

**For** writing fiction.

It reasons through world and plot decisions with you, keeps a story wiki
coherent, and distils your prose voice from evidence rather than from what you
say about it. The wiki is yours and stays yours — the agent reads it and
proposes, and there is no approval ceremony to satisfy.

It drafts and coaches prose, and reads a finished draft back to you — a
reader test, a critique, a scan for machine-prose tells. It does all of that
itself. Where a read only works on fresh eyes, such as reacting to a chapter
with none of the surrounding lore in hand, it can hand that one job to a second
model and file what comes back.

**Needs** a `data/<instance>/writing/` folder for your author voice, and a
notebook folder if you want the story wiki there.

---

## game_designer

**For** designing and building a game, with the technical vocabulary taught as
the work reaches it.

It coaches Socratically through design and build: art direction, world and
mechanics design, and incremental build steps. It defines a term the first time
it comes up and raises the level as you take it on. It will not lock a technical
choice — engine, language, art pipeline — before you understand the trade-off,
and it invents no creative content you did not ask for.

It also stewards `data/<instance>/code_projects/`, the folder holding every
software project you are building with AI help, whether that is one game or
several.

**Needs** a `data/<instance>/code_projects/` folder. Saving a milestone assumes
you have git installed.

---

## client_services

**For** work you do for other people.

Paid client work, a favour for a friend, a volunteer commitment, a grant
collaboration — "client" means the other party, not a billing relationship. It
runs intake for a new engagement, keeps a registry of who and what, holds each
project's own working state, and drafts the operator tasks a project needs.

It drafts and never sends. Submitting a deliverable, contacting a client, and
anything behind a credential is always your own step.

**Needs** a `data/<instance>/clients/` folder, which it builds with you at
intake.

---

## Adding your own

`src/playbooks/create_agent.md` is the procedure, and
`src/templates/identity_template.md` is the shape a charter has to take. A new
agent needs a charter, an entry in the `agents` block of your configuration, and
an epic on the board carrying its slug as owner. `src/playbooks/migrate_legacy_agent.md`
covers bringing in an agent that already exists somewhere else.

### Starting from somebody else's

You can download most of an agent. Nobody publishes whole ones — what the
community publishes is skills, and role descriptions written for other tools,
each a single Markdown file saying what a role does. Both are things you can
bring in.

What arrives: the skills, installed one at a time and inert until you trust
them; the role description, which you read and adopt as the body of a charter;
and the associations — which skills belong to this agent, where its content
lives — which are settings you copy rather than write.

What you decide: the mandate. Who the agent answers to, what stops it, and what
it is not allowed to change. That is a few sentences, and writing them is
minutes rather than an afternoon — but they are yours, because a file that could
grant itself authority is the one thing this system refuses. So downloading a
Product Manager means downloading a product manager's know-how, and the agent it
belongs to is one you create.

`src/templates/identity_template.md` §What of an agent can be imported is the
rule, part by part.
