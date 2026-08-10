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

| Intent | Command |
|--------|---------|
| See everything by status | `wf.py list` |
| What should I work on? | `wf.py next` |
| Park / capture a thread | `wf.py park <id> --next "…" --blocker decision:"…"` |
| Branch a topic | `wf.py branch <parent> "Title" --type claude-code` |
| Resume a thread | `wf.py resume <id>` |
| Refresh the dashboard | `wf.py render` |

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
