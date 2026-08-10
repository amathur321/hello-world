# Wayfinder — architecture

A spatial dashboard for capturing, organizing, and resuming stalled work threads
across Claude Code, Cowork, and chat sessions.

> **The problem this solves.** Ideas hit walls. Sessions pile up. Without a
> capture-and-organize discipline, the threads evaporate. Wayfinder makes two
> things frictionless: (1) capturing state the moment you hit a wall, and
> (2) resuming a stalled thread from anywhere. The star map is how you *see* the
> graph — it is not the source of truth.

## The core loop

```
  branch a topic  ──►  a star appears  ──►  hit a wall → park  ──►  resume anywhere
  (in any chat)        (node written to      (resume-context +       (reopen the exact
   a tangent forks      the graph, bound      typed blocker           session with its
   into its own         to the session         captured)               saved context)
   session)             by tag)
        ▲                                                                    │
        └────────────────────────────────────────────────────────────────────┘
```

A conversation is a *thread*. When it branches into a new topic, that branch
spawns a **node** on the star map. The conversation stays live and interactive in
Claude; the map reflects the constellation and lets you steer it.

## Layers

| Layer            | Responsibility |
|------------------|----------------|
| **Graph store**  | Git-tracked node files in `graph/` — the versioned, portable **source of truth**. Every star is a diffable file. This is the "never lose a thread" guarantee. |
| **Session binding** | Each real session is tagged `starmap:<nodeId>`. Resolves both ways — node → session (stored on the node) and session → node (via `list_sessions(tags=[...])`). Welds a chat to its star across Claude Code, Cowork, and claude.ai. |
| **Wayfinder skill** | The command layer inside chats. `/wf branch`, `/wf park`, `/wf next`, `/wf resume`, `/wf map`. |
| **Dashboard**    | The star map (`prototype/star-map.html`). Your command center — reflects the graph and (phase 2) drives it. |
| **Nudges**       | A weekly routine sweeps for stale frontier stars and surfaces "these have been waiting on a decision only you can make." |

## Data model — a "star" (node)

See `graph/schema.json`. Every node carries:

- **`status`** — `idea` → `open`/`frontier` → `blocked`/`parked` → `resolved`.
  `frontier` = unblocked and ready to advance; that is what the recommender picks from.
- **`session`** — `{ type, ref }` binding to the real chat. `type` ∈
  `claude-code | cowork | chat | none`. `ref` is the session id (also mirrored as
  the `starmap:<id>` tag on that session).
- **`resume`** — `{ last, next }`. `last` = what I was doing; `next` = the exact
  concrete next step. Restarts a stalled thread in seconds, not minutes.
- **`blocker`** — `{ type, detail }`. `type` ∈ `none | decision | dependency |
  research`. Typing the blocker is what lets you filter *"what's blocked on a
  decision I could just make right now."*
- **`triage`** — `{ priority (1-3), effort (S/M/L), energy (deep/light/admin) }`.
  Lets "pick up next" match the time and headspace you actually have.
- **`edges`** — relationships to other nodes: `part-of | depends | blocks | branch`.
- **`doneWhen`** — the acceptance criteria that collapse the star to `resolved`.

## The wayfinder skill (command grammar)

| Command | Effect |
|---------|--------|
| `/wf branch "<topic>"` | Fork a linked session (or a lightweight node with `session.type: none`), add a `branch` edge to the parent, write the node file, tag the session. |
| `/wf park [blocker]` | Snapshot the current session → set `status: parked`, capture `resume.last/next`, record the typed `blocker`, tag the session. |
| `/wf next` | Recommend the top unblocked `frontier` node by priority, then effort/energy fit. |
| `/wf resume <id>` | Reopen the node's bound session and re-seed it with `resume` context. |
| `/wf map` | Regenerate the dashboard from the committed graph. |

Session enumeration, creation, tagging, and messaging use the
`claude-code-remote` MCP tools already available in this environment
(`list_sessions`, `create_session`, `set_session_tags`, `send_message`,
`create_trigger`). That is why this is buildable rather than aspirational.

## Build phases

- **Phase 0 — foundation (this commit).** Data model + schema + example stars +
  interactive prototype. The map renders and demonstrates the branch/park/resume loop.
- **Phase 1 — the skill, usable end to end.** `/wf park`, `/wf branch`, `/wf next`,
  `/wf resume`, `/wf map` operating on the git graph + session tags. Fully usable
  inside Claude Code today — no hosting required.
- **Phase 2 — live dashboard.** Give the map runtime capabilities so branch / park /
  resume fire straight from a node back into the harness. This is where the
  "command center" controls live.
- **Phase 3 — coverage + nudges.** Full Cowork/chat binding + a weekly trigger that
  summarizes stale frontier stars.

## Open decisions

1. **Canonical chat surface** — Cowork vs Claude Code as the default home for
   branched chats. Gates the skill's `/branch` target. *(This is a you-decision,
   not a research task — it appears as a `blocked: decision` star on the map.)*
2. **Auto-capture** — should hitting a wall auto-offer to park, or stay manual?
3. **Dashboard hosting** — regenerated artifact (simple, private) vs a persistent
   live app (needs state). Phase 1 assumes the former.
