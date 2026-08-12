---
description: Wayfinder — capture, park, branch, or resume work threads on the star map
---
Use the **wayfinder** skill to handle this request.

Request: $ARGUMENTS

How to interpret it:
- **(no arguments)** → give me a status read: run `wf.py list` and `wf.py next`,
  then tell me what's waiting on me and what to pick up.
- **park [note]** → capture the current thread — its next concrete step and a
  typed blocker (decision / dependency / research) — and park it. Tag the
  session `starmap:<id>`.
- **branch <topic>** → fork a new star off the current thread (branch edge); if a
  linked session makes sense, spin one up and tag it.
- **next** → recommend the top unblocked frontier star.
- **resume <id>** → reopen that thread's session, seeded with its saved context.

After any change to the graph, run `wf.py render` so the star map stays in sync.
