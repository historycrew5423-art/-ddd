# kiro-workspace

Mirror of my Kiro Web workspace: the full Kiro state, raw session logs, and
readable chat transcripts. Private repo under `historycrew5423-art`.

Everything new goes here by default — each sync copies the entire `/projects/.kiro`
directory and regenerates the transcripts.

## Layout

| Path | What it is |
|------|------------|
| `kiro/` | Full mirror of `/projects/.kiro` — sessions, settings, powers, session index, web-session config. This is the source of truth. |
| `kiro/sessions/<id>/<sub>/messages.jsonl` | Raw, complete session log (every message, tool call, tool result, reasoning). |
| `conversations/` | Human-readable Markdown transcript per session, generated from the raw logs. |
| `scripts/export_transcript.py` | Regenerates the Markdown transcripts from the raw logs. |
| `scripts/sync.sh` | Mirrors `/projects/.kiro`, regenerates transcripts, commits, and pushes. |

## Re-syncing

From inside a Kiro sandbox that has this repo cloned:

```bash
bash scripts/sync.sh
```

## Notes

- No credentials or tokens are stored here. The logs contain environment
  identifiers only (session IDs, instance IDs). Scanned before the first push.
- A fresh sandbox does **not** auto-connect to this repo. Clone it first, then
  run the sync script.
- `kiro/settings/permissions.yaml` is a copy of the sandbox's own trust-boundary
  config, included for completeness.
