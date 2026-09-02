# 0001 — Canonical surface: Claude Code as home, Cowork + chat as spokes

- **Status:** Accepted
- **Date:** 2026-08-11

## Context

Wayfinder threads can start in Claude Code, Cowork, or claude.ai chat. "Which
surface is canonical?" seemed like one question but is really two:

- **A — Where does the source of truth live and get orchestrated?**
- **B — Where do you capture a spark and do the work?**

The graph is git-tracked files in this repo. Only Claude Code operates on that
folder structure natively (CLI writes, `render`, git commit, triggers). But
sparks frequently land in chat or Cowork — often on a phone — and if capture
requires Claude Code, we lose exactly the ideas the system exists to catch.

## Decision

**Claude Code is the canonical home and orchestrator. Cowork and chat are
first-class capture-and-work surfaces, not second-class.** A node stores its
native `session.type`, so `resume` reopens the right kind of session.

- **Home / orchestrator:** always Claude Code (graph writes, render, commit, triggers).
- **Capture:** any surface, near-zero-friction (title + optional link is enough).
- **Execution target:** defaults to Claude Code when a node graduates to work
  that touches the folder structure; otherwise stays on its native surface.

Binding rests on the `starmap:<id>` session tag plus the session ref on the node.
Chat is often **capture-only**: the star and its chat ref are saved, and a Claude
Code session flushes/renders it on the next sync (deferred capture).

## Consequences

- Cross-surface binding depends on tags + stored refs, not on a shared working
  directory. That is an accepted constraint, not a bug.
- Capture must stay trivial on every surface, or the original "lost ideas"
  problem returns.
- `/wf branch` defaults its execution target to Claude Code but honors an
  explicit `--type cowork|chat|none`.

## Revisit when

Cowork gains native, low-friction repo/file access equal to Claude Code's — at
which point "home" could become multi-surface rather than Claude-Code-only.
