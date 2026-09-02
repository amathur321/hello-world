#!/usr/bin/env bash
# Make the /wf command + wayfinder skill available in EVERY Claude Code session
# on this machine (not just when this repo is open), all pointing at one graph.
#
# Run once per machine:  bash .claude/skills/wayfinder/install.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
mkdir -p "$HOME/.claude/skills" "$HOME/.claude/commands"

# Symlink (not copy) so repo updates flow through automatically.
ln -sfn "$REPO/.claude/skills/wayfinder" "$HOME/.claude/skills/wayfinder"
ln -sfn "$REPO/.claude/commands/wf.md"   "$HOME/.claude/commands/wf.md"

# Point the CLI at this repo as the Wayfinder home, from any directory.
printf '{\n  "home": "%s"\n}\n' "$REPO" > "$HOME/.claude/wayfinder.json"

echo "✓ Installed:"
echo "  /wf command      -> ~/.claude/commands/wf.md"
echo "  wayfinder skill  -> ~/.claude/skills/wayfinder"
echo "  graph home       -> $REPO  (~/.claude/wayfinder.json)"
echo
echo "Open a new Claude Code session anywhere and type /wf."
