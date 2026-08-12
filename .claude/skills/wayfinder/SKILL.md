---
name: wayfinder
description: >-
  Capture, organize, and resume stalled work threads on a star map. Use when the
  user wants to park/capture the current thread, branch a topic into its own
  session, ask what to pick up next, resume a stalled thread, or render the star
  map — and PROACTIVELY when the user signals they are stuck, blocked, out of
  time, or want to come back to something later. Triggers: "I'm stuck", "hit a
  wall", "park this", "come back to this", "branch off", "what should I pick up",
  "resume", "star map", "wayfinder", "/wf".
---

# Wayfinder

A spatial system for work threads that stall. The **graph is the source of
truth** (`graph/*.json`, one file per star); the dashboard
(`prototype/star-map.html`) renders it. Full design: `docs/ARCHITECTURE.md`.

Run every graph operation through the CLI so files stay valid:

```
python3 .claude/skills/wayfinder/scripts/wf.py <command>
```

Every star has a **`category`** (a constellation: Research, Product, Tooling, a
project…). The map and `wf.py list` group by it so priority reads by theme. When
capturing or branching, set a category; `branch` inherits the parent's.

| Intent | Command |
|--------|---------|
| See everything grouped by category | `wf.py list` |
| What should I work on? | `wf.py next` |
| Park / capture a thread | `wf.py park <id> --next "…" --blocker decision:"…"` |
| Branch a topic | `wf.py branch <parent> "Title" --type claude-code` |
| Resume a thread | `wf.py resume <id>` |
| Refresh the dashboard | `wf.py render` |
| Backfill from a Claude export | `ingest.py` (see `docs/import-guide.md`), then categorize + file |

## Auto-park (proactive)

When the user signals a wall — "I'm stuck", "let's come back to this", "blocked
on X", "out of time", or trailing off on a hard problem — **offer to park the
current thread** before context is lost. Don't wait to be asked. Do this:

1. Identify the star for the current thread (its `starmap:<id>` session tag), or
   propose creating one if the thread isn't on the map yet.
2. Capture two things in your own words from the conversation: the **next
   concrete step** and the **typed blocker** (`decision` / `dependency` /
   `research` / `none`). A `decision` blocker is the highest-value capture — it's
   something only the user can unblock.
3. Confirm, then `wf.py park <id> --next "…" --blocker <type>:"…"`.
4. If a session is bound, tag it `starmap:<id>` via `set_session_tags`.

Keep it one exchange — capture should feel lighter than the wall did.

## Surfaces

Claude Code is the **canonical home**; Cowork and chat are **first-class,
secondary** surfaces. Keep two roles separate — people conflate them:

- **Home / orchestrator — always Claude Code.** The graph is git-tracked files in
  this repo, so only Claude Code operates on it natively: the CLI writes nodes,
  `render` regenerates the map, git commits it, triggers run here. All
  reconciliation happens here.
- **Capture — any surface.** A star can be born in chat or Cowork (where many
  "branch off" sparks land, often on a phone). Capture must be near-zero-friction
  everywhere: a title + optional link is enough to create a node; triage, edges,
  and render get enriched later from Claude Code.
- **Execution target — defaults to Claude Code** when a node graduates to real
  work that touches the folder structure. But a node keeps its native
  `session.type`, so `resume` reopens the *right kind* of session.

Binding by surface:

- **claude-code** — full: CLI + tag + commit; `create_session` for a new branch.
- **cowork** — create / tag / message via the same `claude-code-remote` MCP
  tools; graph writes reconcile in Claude Code.
- **chat** — lightest, often capture-only: store `session.type: chat` plus the
  chat ref; a Claude Code session flushes and renders it on the next sync. If a
  chat can't reach the repo, treat capture as **deferred** — the spark is saved
  as a node; enrichment happens later.

Rule of thumb: **capture anywhere, orchestrate in Claude Code, resume where it
was born.** Decision record: `docs/decisions/0001-canonical-surface.md`.

## Session binding

Each star binds to a real chat by tag. Use the `claude-code-remote` MCP tools
(load via ToolSearch if needed):

- **branch** → `create_session` for the new topic, then `set_session_tags` with
  `starmap:<newId>` (or tag the current session if branching in place), then
  `wf.py branch`.
- **park** → `set_session_tags` `starmap:<id>` on the current session so it can
  be found again.
- **resume** → find the session (`list_sessions` filtered by the tag) and
  `send_message` it, seeded with the star's `next` step.

Node `session.type` picks the surface: **`claude-code`** is the default target
(richest session tooling); `cowork` for exploratory threads; `chat` for quick
ones; `none` for an idea with no session yet.

## Rendering

After any graph change, run `wf.py render` to rewrite the dashboard's data
block from the graph, then re-publish the artifact (or open the HTML) to view it.
The map has a **mobile glance** mode for scanning "what needs you" on a phone.
