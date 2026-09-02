#!/usr/bin/env python3
"""Wayfinder CLI — operate on the git-tracked star graph.

The graph in graph/*.json is the source of truth. This tool reads and writes
those node files and regenerates the dashboard from them.

Usage:
  wf.py list                          Group every star by status
  wf.py next                          Recommend the top unblocked frontier star
  wf.py park <id> [--next "..."] [--blocker type[:detail]]
                                      Capture context and park a thread
  wf.py branch <parent> "<title>" [--type claude-code|cowork|chat|none]
                                      Fork a new star off a parent (branch edge)
  wf.py resume <id>                   Print resume-context + the bind action to take
  wf.py render [--html PATH]          Rebuild the dashboard data from the graph
"""
import sys, os, json, re, argparse, glob, datetime, math
from wflib import HOME as ROOT, GRAPH, HTML

STATUS_ORDER = ["blocked", "frontier", "open", "parked", "idea", "resolved"]
EFFORT = {"S": 0, "M": 1, "L": 2}


def node_path(nid):
    return os.path.join(GRAPH, nid + ".json")


def load():
    nodes = {}
    for p in glob.glob(os.path.join(GRAPH, "*.json")):
        if os.path.basename(p) == "schema.json":
            continue
        with open(p) as f:
            n = json.load(f)
        nodes[n["id"]] = n
    return nodes


def save(n):
    n["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    with open(node_path(n["id"]), "w") as f:
        json.dump(n, f, indent=2)
        f.write("\n")


def incoming(nodes, nid):
    return [(m["id"], e) for m in nodes.values() for e in m.get("edges", []) if e["to"] == nid]


def is_unblocked(n):
    return (n.get("blocker") or {}).get("type", "none") == "none"


# ---------- commands ----------
def cmd_list(nodes, _a):
    cats = sorted({category(n) for n in nodes.values()})
    for cat in cats:
        members = [n for n in nodes.values() if category(n) == cat and n["status"] != "resolved"]
        if not members:
            continue
        waiting = sum(1 for n in members
                      if n["status"] == "blocked" and (n.get("blocker") or {}).get("type") == "decision")
        tail = f" — {waiting} waiting on you" if waiting else ""
        print(f"\n\033[1m{cat.upper()}\033[0m  ({len(members)} open{tail})")
        order = {s: i for i, s in enumerate(STATUS_ORDER)}
        for n in sorted(members, key=lambda x: (order.get(x["status"], 9), x["triage"]["priority"])):
            sess = (n.get("session") or {}).get("ref") or "—"
            print(f"  {n['status']:<9} P{n['triage']['priority']} {n['title']:<40} "
                  f"[{(n.get('session') or {}).get('type','none')}:{sess}]")
    print()


def cmd_next(nodes, _a):
    cand = [n for n in nodes.values() if n["status"] == "frontier" and is_unblocked(n)]
    cand.sort(key=lambda n: (n["triage"]["priority"], EFFORT.get(n["triage"]["effort"], 1)))
    if not cand:
        print("No unblocked frontier stars. Resolve a blocker to light one up.")
        return
    top = cand[0]
    print(f"\n\033[1mPick up next:\033[0m {top['title']}  ({top['id']})")
    print(f"  frontier · unblocked · P{top['triage']['priority']} · {top['triage']['effort']} · {top['triage']['energy']}")
    print(f"  next → {top['resume']['next']}")
    if len(cand) > 1:
        print("  also ready: " + ", ".join(f"{n['id']}" for n in cand[1:]))
    print()


def cmd_park(nodes, a):
    n = nodes.get(a.id)
    if not n:
        sys.exit(f"no such star: {a.id}")
    n["status"] = "parked"
    if a.next:
        n["resume"]["next"] = a.next
    if a.blocker:
        t, _, d = a.blocker.partition(":")
        n["blocker"] = {"type": t} if not d else {"type": t, "detail": d}
    save(n)
    print(f"Parked {a.id}. Context captured. (run: wf.py render to refresh the map)")


def slug(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24]
    return s or "star"


def cmd_branch(nodes, a):
    parent = nodes.get(a.parent)
    if not parent:
        sys.exit(f"no such parent star: {a.parent}")
    nid = slug(a.title)
    while nid in nodes:
        nid += "-2"
    px, py = (parent.get("pos") or {"x": 600, "y": 400}).values()
    k = len([1 for m in nodes.values() for e in m.get("edges", [])
             if e["to"] == a.parent and e["kind"] == "branch"])
    import math
    ang = 0.9 + k * 1.4
    node = {
        "id": nid, "title": a.title, "category": category(parent), "status": "idea",
        "session": {"type": a.type, "ref": None},
        "resume": {"last": f'Branched off "{parent["title"]}"', "next": "Give it a first concrete step"},
        "blocker": {"type": "none"},
        "triage": {"priority": 3, "effort": "M", "energy": parent["triage"]["energy"]},
        "edges": [{"to": a.parent, "kind": "branch"}],
        "doneWhen": ["(define what done looks like)"],
        "pos": {"x": round(px + math.cos(ang) * 95), "y": round(py + math.sin(ang) * 95)},
    }
    save(node)
    print(f"Created star {nid}, branched off {a.parent}.")
    print(f"  Bind a session: tag it starmap:{nid} (create_session for a new chat, or set_session_tags on the current one).")
    print(f"  Then: wf.py render")


def cmd_resume(nodes, a):
    n = nodes.get(a.id)
    if not n:
        sys.exit(f"no such star: {a.id}")
    s = n.get("session") or {}
    print(f"\n\033[1m{n['title']}\033[0m  ({n['id']}) — {n['status']}")
    print(f"  last → {n['resume']['last']}")
    print(f"  next → {n['resume']['next']}")
    b = n.get("blocker") or {"type": "none"}
    if b["type"] != "none":
        print(f"  blocker ({b['type']}) → {b.get('detail','')}")
    if s.get("ref"):
        print(f"\n  To resume: reopen session {s['ref']} ({s.get('type')}) — tag starmap:{n['id']}")
        print(f"  Via MCP: send_message to {s['ref']} seeded with the 'next' step above.")
    else:
        print("\n  No session bound yet — create one and tag it starmap:" + n["id"])
    print()


# ---------- render ----------
def derive_r(nodes, n):
    base = {1: 19, 2: 15, 3: 12}[n["triage"]["priority"]]
    if len(incoming(nodes, n["id"])) >= 3:
        base += 6
    return base


CAT_COLORS = ["#8b7ff0", "#4bb7c9", "#d59a4a", "#d47a9a", "#7bc47f", "#c98bd4", "#e0a458"]


def category(n):
    return n.get("category") or "Uncategorized"


def layout(nodes):
    """Group stars into category constellations and place each cluster in its own
    region of the sky. Returns category metadata; mutates node pos in-memory."""
    cats = sorted({category(n) for n in nodes.values()})
    cx, cy = 600, 380
    ring = 150 + len(cats) * 40
    meta = []
    for i, cat in enumerate(cats):
        ang = -math.pi / 2 + 2 * math.pi * i / len(cats)
        ccx = cx + (ring * math.cos(ang) if len(cats) > 1 else 0)
        ccy = cy + (ring * math.sin(ang) * 0.82 if len(cats) > 1 else 0)
        members = sorted([n for n in nodes.values() if category(n) == cat],
                         key=lambda n: (n["triage"]["priority"], n["id"]))
        m = len(members)
        cluster_r = 46 + m * 13
        for j, node in enumerate(members):
            if m == 1:
                nx, ny = ccx, ccy
            else:
                a = 2 * math.pi * j / m + i * 0.7
                rr = cluster_r * 0.6
                nx, ny = ccx + rr * math.cos(a), ccy + rr * math.sin(a)
            node["pos"] = {"x": round(nx), "y": round(ny)}
        meta.append({"name": cat, "color": CAT_COLORS[i % len(CAT_COLORS)],
                     "cx": round(ccx), "cy": round(ccy), "r": round(cluster_r), "count": m})
    return meta


def to_js(nodes, cats_meta):
    js_nodes, js_edges = [], []
    for n in sorted(nodes.values(), key=lambda x: x["id"]):
        pos = n.get("pos") or {"x": 600, "y": 400}
        sess = n.get("session") or {}
        js_nodes.append({
            "id": n["id"], "t": n["title"], "cat": category(n), "status": n["status"],
            "type": sess.get("type", "none"), "x": pos["x"], "y": pos["y"],
            "r": derive_r(nodes, n),
            "prio": n["triage"]["priority"], "effort": n["triage"]["effort"],
            "energy": n["triage"]["energy"], "blocker": n.get("blocker", {"type": "none"}),
            "sess": sess.get("ref"), "last": n["resume"]["last"], "next": n["resume"]["next"],
            "done": n.get("doneWhen", []),
        })
        for e in n.get("edges", []):
            kind = "partof" if e["kind"] == "part-of" else e["kind"]
            js_edges.append({"from": n["id"], "to": e["to"], "kind": kind})
    nl = "  let nodes = [\n" + ",\n".join("    " + json.dumps(o) for o in js_nodes) + "\n  ];\n"
    el = "  let edges = [\n" + ",\n".join("    " + json.dumps(o) for o in js_edges) + "\n  ];\n"
    cl = "  let cats = " + json.dumps(cats_meta) + ";\n"
    return nl + el + cl


def cmd_render(nodes, a):
    path = a.html or HTML
    with open(path) as f:
        html = f.read()
    cats_meta = layout(nodes)
    block = "\n" + to_js(nodes, cats_meta)
    new, n = re.subn(r"(/\*WF_DATA_START\*/).*?(/\*WF_DATA_END\*/)",
                     lambda m: m.group(1) + block + "  " + m.group(2), html, flags=re.S)
    if not n:
        sys.exit("could not find /*WF_DATA_START*/.../*WF_DATA_END*/ markers in " + path)
    with open(path, "w") as f:
        f.write(new)
    csum = ", ".join(f"{c['name']} ({c['count']})" for c in cats_meta)
    print(f"Rendered {len(nodes)} stars in {len(cats_meta)} constellations: {csum}")
    print(f"  -> {os.path.relpath(path, ROOT)}. Re-publish the artifact (or open the file) to see it.")


def main():
    p = argparse.ArgumentParser(prog="wf.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("next")
    pp = sub.add_parser("park"); pp.add_argument("id"); pp.add_argument("--next"); pp.add_argument("--blocker")
    pb = sub.add_parser("branch"); pb.add_argument("parent"); pb.add_argument("title"); pb.add_argument("--type", default="none")
    pr = sub.add_parser("resume"); pr.add_argument("id")
    prn = sub.add_parser("render"); prn.add_argument("--html")
    a = p.parse_args()
    nodes = load()
    {"list": cmd_list, "next": cmd_next, "park": cmd_park, "branch": cmd_branch,
     "resume": cmd_resume, "render": cmd_render}[a.cmd](nodes, a)


if __name__ == "__main__":
    main()
