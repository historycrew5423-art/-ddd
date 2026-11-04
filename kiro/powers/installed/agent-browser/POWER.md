---
name: agent-browser
description: "Lightweight CLI-driven browser automation (vercel-labs/agent-browser) — navigate, click, type, and snapshot pages via isolated sessions"
displayName: "Agent Browser"
keywords: ["agent-browser", "browser", "navigate", "snapshot", "click", "session"]
---

## Agent Browser

[agent-browser](https://github.com/vercel-labs/agent-browser) is a CLI-first browser automation tool for navigating and interacting with live web pages. Invoke it directly as the `agent-browser` CLI via the shell — it does not run as an MCP server. A named `--session` persists one browser context across separate invocations.

### Usage

```bash
agent-browser --session <name> open "https://example.com"
agent-browser --session <name> snapshot                       # accessibility tree with stable element refs
agent-browser --session <name> click "<@ref-or-selector>"
agent-browser --session <name> type "<@ref-or-selector>" "text"
agent-browser --session <name> screenshot /projects/sandbox/.kiro/artifacts/screenshots/<timestamp>-<label>.png
```

Run `agent-browser skills get core --full` for the full command reference and copy-paste examples.

### Capabilities

- `open` / `navigate` / `back` / `forward` / `reload` — page navigation
- `click` / `type` / `fill` / `check` / `uncheck` / `select` / `press` / `hover` / `drag` — element interaction
- `snapshot` — accessibility-tree snapshot with stable element refs
- `screenshot` — visual capture written to the artifacts directory
- `eval` — run JavaScript in the page
- `tab` — multi-tab management
- `wait` — wait for an element or a fixed time
- Named `--session` for isolated, parallel browser contexts

### Constraints

- Headless only — no display server is available in the sandbox.
- Each `--session` name maps to an isolated browser context; do not reuse a session across unrelated tasks.
- Screenshots must use an absolute path under `/projects/sandbox/.kiro/artifacts/screenshots/<timestamp>-<label>.png`. `~` is not expanded by the CLI and would create a literal `~` directory.
- Artifacts quota: 10 MB per artifact, 500 MB total, 200 artifacts per session. If a quota is exceeded, prune the oldest artifacts first rather than disabling capture, and surface the quota error rather than silently skipping a requested capture.
