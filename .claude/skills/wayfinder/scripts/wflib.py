"""Locate the Wayfinder home (the repo holding graph/, prototype/, import/).

Lets the skill + CLI run from ANY directory / any Claude Code session, not just
from inside the star-map repo. Resolution order:

  1. $WAYFINDER_HOME                     (explicit override)
  2. ~/.claude/wayfinder.json -> "home"  (written by install.sh)
  3. walk up from the current directory  (in-repo usage)
  4. fall back to this file's repo layout (…/.claude/skills/wayfinder/scripts)
"""
import os, json


def _valid(h):
    return h and os.path.isdir(os.path.join(h, "graph"))


def find_home():
    env = os.environ.get("WAYFINDER_HOME")
    if _valid(env):
        return os.path.abspath(env)

    cfg = os.path.expanduser("~/.claude/wayfinder.json")
    if os.path.isfile(cfg):
        try:
            h = json.load(open(cfg)).get("home")
            if _valid(h):
                return os.path.abspath(h)
        except Exception:
            pass

    d = os.getcwd()
    while True:
        if os.path.isfile(os.path.join(d, "graph", "schema.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


HOME = find_home()
GRAPH = os.path.join(HOME, "graph")
HTML = os.path.join(HOME, "prototype", "star-map.html")
IMPORT = os.path.join(HOME, "import")
