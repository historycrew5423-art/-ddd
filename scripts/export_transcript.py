#!/usr/bin/env python3
"""Convert Kiro session logs (messages.jsonl) into readable Markdown transcripts.

For every session under /projects/.kiro/sessions/*/*/messages.jsonl this writes
a Markdown file into conversations/. The raw .jsonl stays the source of truth
(mirrored under kiro/); this is just the human-readable view.
"""
import json
import glob
import os
import sys

KIRO_ROOT = "/projects/.kiro"
SESS_GLOB = os.path.join(KIRO_ROOT, "sessions", "*", "*", "messages.jsonl")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_DIR, "conversations")


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def session_meta(sess_dir):
    meta = {}
    sj = os.path.join(sess_dir, "session.json")
    if os.path.exists(sj):
        try:
            meta = json.load(open(sj, encoding="utf-8"))
        except Exception:
            pass
    return meta


def fmt_args(args):
    try:
        s = json.dumps(args, ensure_ascii=False)
    except Exception:
        s = str(args)
    s = s.replace("\n", " ")
    return s if len(s) <= 400 else s[:400] + " …"


def render(rows):
    out = []
    for d in rows:
        p = d.get("payload", {}) or {}
        t = p.get("type")
        if t == "user":
            c = (p.get("content") or "").strip()
            if c:
                out.append(f"\n## 👤 用户\n\n{c}\n")
        elif t == "assistant":
            op = p.get("operationType")
            c = (p.get("content") or "").strip()
            if not c:
                continue
            if op == "Say":
                out.append(f"\n## 🤖 Kiro\n\n{c}\n")
            elif op == "Reasoning":
                out.append(
                    "\n<details><summary>🤔 思考过程</summary>\n\n"
                    + c
                    + "\n\n</details>\n"
                )
            else:
                out.append(f"\n## 🤖 Kiro\n\n{c}\n")
        elif t == "tool_call":
            name = p.get("name") or p.get("toolName") or p.get("tool") or "?"
            args = (
                p.get("arguments")
                or p.get("input")
                or p.get("args")
                or p.get("parameters")
                or {}
            )
            out.append(f"\n> 🔧 工具调用 `{name}`\n>\n> `{fmt_args(args)}`\n")
    return "\n".join(out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = sorted(glob.glob(SESS_GLOB))
    if not paths:
        print("no session logs found", file=sys.stderr)
        return 0
    written = []
    for path in paths:
        sess_dir = os.path.dirname(path)
        meta = session_meta(sess_dir)
        rows = load(path)
        title = meta.get("title") or "untitled-session"
        model = meta.get("modelId", "?")
        created = meta.get("createdAt", "")
        modified = meta.get("lastModifiedAt", "")
        sess_id = meta.get("id") or os.path.basename(sess_dir)
        date = (created or "")[:10] or "undated"
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in title).strip("-")
        fname = f"{date}-{safe}-{sess_id[:8]}.md"
        header = (
            f"# {title}\n\n"
            f"- Session ID: `{sess_id}`\n"
            f"- Model: `{model}`\n"
            f"- Created: {created}\n"
            f"- Last modified: {modified}\n"
            f"- Raw log: `kiro/sessions/{os.path.relpath(path, os.path.join(KIRO_ROOT, 'sessions'))}`\n\n"
            "---\n"
        )
        body = render(rows)
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8") as fh:
            fh.write(header + body + "\n")
        written.append(fname)
    print("wrote: " + ", ".join(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
