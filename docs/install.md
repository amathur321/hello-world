# Install: make `/wf` work everywhere

By default the `/wf` command and the wayfinder skill are **project-scoped** —
they load in a Claude Code session that has *this* repo open. This is the setup
to get them in **every** Claude Code session on a machine, all pointing at one
star-map graph.

## One-time, per machine (desktop / CLI Claude Code)

Clone this repo somewhere permanent, then run:

```
bash .claude/skills/wayfinder/install.sh
```

It symlinks into `~/.claude` (so repo updates flow through automatically) and
writes `~/.claude/wayfinder.json` pointing at your clone:

- `~/.claude/commands/wf.md`     → the `/wf` command
- `~/.claude/skills/wayfinder`   → the skill
- `~/.claude/wayfinder.json`     → `{ "home": "<your repo path>" }`

Open a new session anywhere and type `/wf`.

## How the graph is located

The CLI resolves the star-map "home" (the repo with `graph/`) in this order:

1. `$WAYFINDER_HOME` — explicit override for one command/session.
2. `~/.claude/wayfinder.json` → `home` — what `install.sh` writes.
3. Walk up from the current directory — so it just works inside the repo.
4. Fallback to the skill's own repo layout.

## The honest caveats

- **Claude Code on the web** runs in an ephemeral container: its `~/.claude`
  resets between sessions, so a user-level install does **not** persist there.
  For web work, keep doing wayfinder from a session that has this repo (where
  `/wf` and the skill are already present), or add them to another repo you open.
- **Cowork / chat** have no skills or file access, so `/wf` does not exist there
  regardless of install — those surfaces are covered by the export backfill
  (`docs/import-guide.md`), not by this command.
- One graph, one home: point every machine at the **same** repo clone so all your
  stars live in one place.
