#!/usr/bin/env python3
"""Ingest a Claude data export into staged stars for review.

Reads a Claude conversation export (the `conversations.json` you get from
claude.ai -> Settings -> Privacy -> Export data) and stages one lightweight
record per conversation. A later AI categorization pass proposes a taxonomy and
promotes staged records into real stars in graph/.

Privacy: raw exports and staged records live under import/ (gitignored) and are
NOT committed. Only derived stars (title, short snippet, dates, category) get
committed to the graph. Tolerant of schema variation across export versions.

Usage:
  ingest.py [--file PATH] [--surface chat|cowork|code] [--max-snippet N]
"""
import sys, os, json, glob, argparse, re
from wflib import HOME as ROOT, GRAPH, IMPORT


def find_export(explicit):
    if explicit:
        return explicit
    cands = []
    for pat in ("conversations.json", "*.json"):
        cands += glob.glob(os.path.join(IMPORT, pat))
    cands = [c for c in cands if os.path.basename(c) not in ("staged.json",)]
    if not cands:
        sys.exit(f"No export found. Put your Claude export at {os.path.relpath(IMPORT, ROOT)}/conversations.json "
                 f"(see docs/import-guide.md).")
    return cands[0]


def load(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        for k in ("conversations", "data", "items"):
            if isinstance(data.get(k), list):
                return data[k]
        return [data]
    if isinstance(data, list):
        return data
    sys.exit("Unrecognized export shape — expected a list of conversations.")


def first(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, "", []):
            return d[k]
    return default


def msg_text(m):
    t = first(m, "text", "content", "body", default="")
    if isinstance(t, list):  # some exports use content blocks
        t = " ".join(b.get("text", "") for b in t if isinstance(b, dict))
    return (t or "").strip()


def is_user(m):
    role = str(first(m, "sender", "role", "author", default="")).lower()
    return role in ("human", "user")


def parse(conv, max_snippet):
    cid = first(conv, "uuid", "id", "conversation_id", default="")
    msgs = first(conv, "chat_messages", "messages", "chat", default=[]) or []
    fu = next((msg_text(m) for m in msgs if is_user(m)), "")
    title = first(conv, "name", "title", default="") or (fu[:60] if fu else "Untitled")
    snippet = re.sub(r"\s+", " ", fu)[:max_snippet]
    return {
        "src": cid,
        "title": title.strip(),
        "created": first(conv, "created_at", "created", default=""),
        "updated": first(conv, "updated_at", "updated", "created_at", default=""),
        "messages": len(msgs),
        "snippet": snippet,
    }


def already_filed():
    refs = set()
    for p in glob.glob(os.path.join(GRAPH, "*.json")):
        if os.path.basename(p) == "schema.json":
            continue
        try:
            n = json.load(open(p))
            ref = (n.get("session") or {}).get("ref")
            if ref:
                refs.add(ref)
        except Exception:
            pass
    return refs


def month_hist(records):
    hist = {}
    for r in records:
        m = (r.get("updated") or r.get("created") or "")[:7]
        if m:
            hist[m] = hist.get(m, 0) + 1
    return dict(sorted(hist.items()))


# ---------- Claude Code local sessions ( ~/.claude/projects/<proj>/<id>.jsonl ) ----------
def code_text(msg):
    if not isinstance(msg, dict):
        return ""
    c = msg.get("content")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, list):
        out = []
        for b in c:
            if isinstance(b, dict) and b.get("type") == "text":
                out.append(b.get("text", ""))
            elif isinstance(b, str):
                out.append(b)
        return " ".join(out).strip()
    return ""


def parse_code_session(path, max_snippet):
    sid = os.path.splitext(os.path.basename(path))[0]
    project = os.path.basename(os.path.dirname(path))
    first_text, msgs, tss = "", 0, []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("timestamp"):
                    tss.append(d["timestamp"])
                t = d.get("type")
                if t in ("user", "assistant"):
                    msgs += 1
                if t == "user" and not first_text:
                    first_text = code_text(d.get("message"))
    except Exception:
        return None
    snippet = re.sub(r"\s+", " ", first_text)[:max_snippet]
    return {
        "src": sid,
        "title": (first_text[:60].strip() if first_text else "Claude Code session"),
        "created": tss[0] if tss else "",
        "updated": tss[-1] if tss else "",
        "messages": msgs,
        "snippet": snippet,
        "project": project,
    }


def collect_code(projects_dir, max_snippet):
    out = []
    for path in glob.glob(os.path.join(projects_dir, "*", "*.jsonl")):
        r = parse_code_session(path, max_snippet)
        if r and r["messages"] > 0:
            out.append(r)
    return out


def main():
    p = argparse.ArgumentParser(prog="ingest.py")
    p.add_argument("--source", default="chat", choices=["chat", "code"],
                   help="chat = a claude.ai export JSON; code = local Claude Code session logs")
    p.add_argument("--file", help="chat export path (defaults to import/conversations.json)")
    p.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"),
                   help="where Claude Code stores local session transcripts")
    p.add_argument("--max-snippet", type=int, default=240)
    a = p.parse_args()

    os.makedirs(IMPORT, exist_ok=True)
    filed = already_filed()

    if a.source == "code":
        raw = collect_code(a.projects_dir, a.max_snippet)
        origin = a.projects_dir
    else:
        path = find_export(a.file)
        raw = [parse(c, a.max_snippet) for c in load(path)]
        origin = os.path.relpath(path, ROOT)

    records, skipped = [], 0
    for r in raw:
        r["surface"] = a.source
        if r.get("src") and r["src"] in filed:
            skipped += 1
            continue
        records.append(r)
    records.sort(key=lambda r: r.get("updated", ""), reverse=True)

    with open(os.path.join(IMPORT, "staged.json"), "w") as f:
        json.dump(records, f, indent=2)

    # a compact, human-scannable digest (local only)
    lines = [f"# Import digest — {len(records)} new {a.source} sessions", ""]
    hist = month_hist(records)
    if hist:
        lines.append("By month: " + "  ".join(f"{k}:{v}" for k, v in hist.items()))
        lines.append("")
    has_proj = any(r.get("project") for r in records)
    lines.append("| updated | msgs | " + ("project | " if has_proj else "") + "title | opening snippet |")
    lines.append("|---|---|" + ("---|" if has_proj else "") + "---|---|")
    for r in records:
        t = r["title"].replace("|", "/")[:60]
        s = r["snippet"].replace("|", "/")[:80]
        proj = (r.get("project", "").replace("|", "/")[:24] + " | ") if has_proj else ""
        lines.append(f"| {(r['updated'] or '')[:10]} | {r['messages']} | {proj}{t} | {s} |")
    with open(os.path.join(IMPORT, "inbox.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Ingested {a.source} from {origin}")
    print(f"  staged {len(records)} new, skipped {skipped} already filed")
    if hist:
        print("  span: " + min(hist) + " -> " + max(hist))
    print(f"  -> import/staged.json + import/inbox.md (gitignored)")
    print("Next: paste import/inbox.md back to Claude to categorize + file (or run the categorization pass).")


if __name__ == "__main__":
    main()
