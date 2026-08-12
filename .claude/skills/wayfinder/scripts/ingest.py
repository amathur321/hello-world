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


def main():
    p = argparse.ArgumentParser(prog="ingest.py")
    p.add_argument("--file")
    p.add_argument("--surface", default="chat", choices=["chat", "cowork", "code"])
    p.add_argument("--max-snippet", type=int, default=240)
    a = p.parse_args()

    os.makedirs(IMPORT, exist_ok=True)
    path = find_export(a.file)
    convs = load(path)
    filed = already_filed()

    records, skipped = [], 0
    for c in convs:
        r = parse(c, a.max_snippet)
        r["surface"] = a.surface
        if r["src"] and r["src"] in filed:
            skipped += 1
            continue
        records.append(r)
    records.sort(key=lambda r: r.get("updated", ""), reverse=True)

    with open(os.path.join(IMPORT, "staged.json"), "w") as f:
        json.dump(records, f, indent=2)

    # a compact, human-scannable digest (local only)
    lines = [f"# Import digest — {len(records)} new conversations ({a.surface})", ""]
    hist = month_hist(records)
    if hist:
        lines.append("By month: " + "  ".join(f"{k}:{v}" for k, v in hist.items()))
        lines.append("")
    lines.append("| updated | msgs | title | opening snippet |")
    lines.append("|---|---|---|---|")
    for r in records:
        t = r["title"].replace("|", "/")[:60]
        s = r["snippet"].replace("|", "/")[:80]
        lines.append(f"| {(r['updated'] or '')[:10]} | {r['messages']} | {t} | {s} |")
    with open(os.path.join(IMPORT, "inbox.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Parsed {len(convs)} conversations from {os.path.relpath(path, ROOT)}")
    print(f"  staged {len(records)} new, skipped {skipped} already filed")
    if hist:
        print("  span: " + min(hist) + " -> " + max(hist))
    print(f"  -> import/staged.json + import/inbox.md (gitignored)")
    print("Next: run the AI categorization pass to propose a taxonomy and file these as stars.")


if __name__ == "__main__":
    main()
