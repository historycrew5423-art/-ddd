#!/usr/bin/env bash
# Sync the entire Kiro state + readable transcripts into this repo and push.
# Safe to run repeatedly. Run from anywhere.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KIRO_SRC="/projects/.kiro"

echo "==> Mirroring ${KIRO_SRC} -> ${REPO_DIR}/kiro"
rm -rf "${REPO_DIR}/kiro"
cp -a "${KIRO_SRC}" "${REPO_DIR}/kiro"

# Drop volatile / meaningless files.
find "${REPO_DIR}/kiro" -type f -name '*.lock' -delete 2>/dev/null || true
find "${REPO_DIR}/kiro" -type f -name '.sync.lock' -delete 2>/dev/null || true
find "${REPO_DIR}/kiro" -type s -delete 2>/dev/null || true   # sockets, if any
# Drop Kiro's internal file-snapshot store: it mirrors the workspace (including
# this repo), so keeping it would nest copies recursively on every sync.
find "${REPO_DIR}/kiro/sessions" -type d -name snapshots -prune -exec rm -rf {} + 2>/dev/null || true

echo "==> Regenerating readable transcripts"
python3 "${REPO_DIR}/scripts/export_transcript.py"

echo "==> Committing and pushing"
cd "${REPO_DIR}"
git add -A
if git diff --cached --quiet; then
  echo "nothing to commit"
else
  git commit -m "Sync Kiro workspace $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push
fi
echo "==> Done"
