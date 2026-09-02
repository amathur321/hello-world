# Backfill: import your Claude history

The one-time pass that clears the backlog. You export your Claude conversations;
an AI pass reviews all of them, proposes a taxonomy, and files each as a star in
the folder structure. This is the "too many to review manually" fix.

## 1. Export your data from Claude

- On **claude.ai** → **Settings** → **Privacy** → **Export data** (menu labels
  may vary slightly). Claude emails you a download link; inside is a
  `conversations.json` (plus a few other files).
- This covers your **chat** history. Claude Code Remote sessions come in through
  the live API instead (the weekly Routine, step 2 of the plan). Cowork isn't
  exportable today — those get captured going forward by the `/wf` skill.

## 2. Drop it in the repo

Put the file at:

```
import/conversations.json
```

`import/` is **gitignored** — your raw chats never get pushed to GitHub. Only the
derived stars (title, a short opening snippet, dates, and the category we assign)
get committed. Note this container is ephemeral: the raw export under `import/`
disappears when the session ends, but the filed stars persist in `graph/`.

## 3. Tell me it's there

I then run, in order:

1. `ingest.py --surface chat` — parses the export into `import/staged.json`
   (lightweight records; skips anything already filed, so re-runs are safe).
2. **AI categorization pass** — I read the staged records, propose a taxonomy
   **bottom-up from what's actually in your history** (this is the review you
   wanted done for you), and show it to you for approval before filing.
3. On your OK — promote the staged records into real stars in `graph/`,
   `render` the map, and commit. Your backlog is now a constellation.

## Also backfill your local Claude Code sessions

Claude Code stores every local session on disk at
`~/.claude/projects/<project>/<session-id>.jsonl`. To pull those onto the map,
run this on each machine you code from:

```
python3 .claude/skills/wayfinder/scripts/ingest.py --source code
```

It scans your local session logs and stages them (title from the opening
message, message count, dates, and the **project folder** — a strong category
signal). Paste the resulting `import/inbox.md` back the same way.

Coverage caveat: this reads **local** sessions on that machine's disk. Sessions
you ran in the **cloud** (web / remote) don't live on your disk — they're only
visible via the live API and are handled by the weekly Routine going forward.
Run `--source code` on every machine you code from to catch them all.

## Controls

- **Snippet length** — `ingest.py --max-snippet N` (default 240 chars) caps how
  much of each opening message is stored on a star.
- **Nothing auto-published** — you approve the taxonomy before anything is filed
  or committed.
- **Anything off-limits** — tell me categories or topics to skip and they stay
  out of the graph entirely.
