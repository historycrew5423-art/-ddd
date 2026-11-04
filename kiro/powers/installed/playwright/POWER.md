---
name: playwright
description: "Browser automation via Playwright — navigate pages, interact with elements, and capture screenshots as session artifacts"
displayName: "Playwright"
keywords: ["playwright", "browser", "screenshot", "web", "automation", "click", "navigate"]
---

## Playwright Browser Automation

For tasks that require interacting with or inspecting live web pages.

### Capabilities

- Navigate to URLs, click elements, fill forms, and read page content
- Take screenshots of the current page or a specific element

### Artifact Capture

Screenshots are written to `/projects/sandbox/.kiro/artifacts/screenshots/` (the configured output directory) and are automatically retrievable by the client through the existing file retrieval APIs. Artifacts quota: 10 MB per artifact, 500 MB total, 200 artifacts per session. If a quota is exceeded, prune the oldest artifacts first rather than disabling capture, and surface the quota error rather than silently skipping a requested capture.

### Constraints

- Headless only — no display server is available in the sandbox.
- `--no-sandbox` is required since the browser process already runs inside the sandbox's own isolation layer; do not attempt to enable nested sandboxing.
