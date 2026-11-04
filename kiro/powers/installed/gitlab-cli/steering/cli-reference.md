# glab CLI Reference — Gateway Environment

On-demand reference for working with `glab` in this environment. Read this when a
`glab` command fails or you need an API recipe. The happy-path workflow lives in
POWER.md; this file explains *why* commands fail and gives the exact fallbacks.

## Why glab subcommands fail here (read this first)

Project-scoped `glab` subcommands (`mr`, `issue`, `ci`, `label`, `release`, …)
resolve the target project by matching your git remote's hostname against the
configured GitLab host. In this environment traffic routes through an
authenticated gateway, so the configured host contains a path prefix while the
git remote host does not — the match fails and the command errors with:

> None of the git remotes configured for this repository correspond to the GITLAB_HOST environment variable.

Two consequences:

1. **Always pass `--repo {owner}/{project}`** — it bypasses remote lookup for most read/update commands.
2. **`glab mr create` fails even with `--repo`** (it insists on remote matching). Use `glab api` (below).

**Never work around this by changing configuration.** Do NOT unset or modify
`GITLAB_HOST`, do NOT run `glab auth login` or `glab config set host`, and do NOT
add extra git remotes. The environment is pre-configured; config changes break
authentication without fixing routing. Never print token values
(`$GITLAB_TOKEN`, token files) — not to debug, not to verify.

## glab api — the universal fallback

`glab api` calls the GitLab REST API directly, skipping project resolution.
It works for everything the REST API supports.

```bash
glab api <endpoint> [-X METHOD] [-f key=value]...
```

- URL-encode `/` in the project path: `owner/project` → `owner%2Fproject`
- Methods: GET (default), `-X POST` (create), `-X PUT` (update), `-X DELETE`
- Query params go in the URL: `glab api "projects/:id/merge_requests?state=merged&per_page=100"`
- Pagination: default page size is 20; add `per_page=100` and `page=N` for more
- GraphQL is NOT supported by the gateway — REST endpoints only

In the recipes below, `:id` means the URL-encoded project path (`owner%2Fproject`)
and endpoints are prefixed `projects/:id/`.

## Merge requests

```bash
# Create (glab mr create ALWAYS fails here — this is the way).
# Set target_branch to the project default — glab api "projects/:id" --jq .default_branch — not "main".
glab api "projects/:id/merge_requests" -X POST \
  -f source_branch=BRANCH -f target_branch=<default> -f title="..." -f description="..."

# Draft MR: prefix the title
-f title="Draft: ..."

# Cross-fork MR: push the branch to the fork, then add
-f source_project_id=FORK_PROJECT_ID

# Read/update (subcommands work with --repo)
glab mr list --repo OWNER/PROJ [--merged|--closed|--all]   # no --state flag
glab mr view IID --repo OWNER/PROJ [--output json]         # json for parsing
glab mr diff IID --repo OWNER/PROJ
glab mr merge IID --repo OWNER/PROJ --yes                  # --yes avoids the prompt
glab mr note IID --repo OWNER/PROJ -m "comment"
glab mr note list --repo OWNER/PROJ IID

# Discussions (no subcommand exists)
glab api "projects/:id/merge_requests/IID/discussions"

# Approve / close / reopen via API
glab api "projects/:id/merge_requests/IID/approve" -X POST
glab api "projects/:id/merge_requests/IID" -X PUT -f state_event=close
```

## Issues

```bash
glab issue create --repo OWNER/PROJ -t "title" -d "description"
glab issue list --repo OWNER/PROJ
glab issue view IID --repo OWNER/PROJ --comments    # comments: there is NO `issue note list`
glab issue note IID --repo OWNER/PROJ -m "comment"  # create a note
glab issue close IID --repo OWNER/PROJ
glab api "projects/:id/issues/IID" -X PUT -f state_event=reopen
glab api "projects/:id/issues/IID" -X DELETE
```

## Labels, milestones, variables

```bash
glab api "projects/:id/labels" -X POST -f name="bug" -f color="#ff0000"
glab api "projects/:id/labels/bug" -X PUT -f new_name="bugfix"      # rename: new_name in body
glab api "projects/:id/labels/bugfix" -X DELETE

glab api "projects/:id/milestones" -X POST -f title="v1.0" -f due_date="2026-12-31"
glab api "projects/:id/milestones/MID" -X PUT -f state_event=close  # DELETE returns 404 — close instead

glab api "projects/:id/variables" -X POST -f key=MY_VAR -f value=v
glab api "projects/:id/variables/MY_VAR" -X PUT -f value=new
glab api "projects/:id/variables/MY_VAR" -X DELETE
```

## Releases and tags

A release's tag must exist on the remote, OR pass `ref` to auto-create it:

```bash
glab api "projects/:id/releases" -X POST \
  -f tag_name=v1.0 -f ref=main -f name="Release v1.0" -f description="notes"
# Without ref and without the tag pushed → HTTP 422
```

## CI/CD

CI commands need a `.gitlab-ci.yml` in the repo. Without one: pipeline lists are
empty, `glab ci status` reports "No pipeline exists" (that's data, not an error),
and triggering a pipeline returns 404.

```bash
glab ci list --repo OWNER/PROJ
glab api "projects/:id/pipelines/PID/jobs"
glab api "projects/:id/jobs/JID/trace"        # job log
glab api "projects/:id/jobs/JID/retry" -X POST
```

## Repo, user, misc

```bash
glab repo view OWNER/PROJ
glab repo fork OWNER/PROJ --clone=false       # --clone=false avoids an interactive hang
glab api "projects/:id/repository/contributors"
glab api "projects/:id/repository/branches"
glab api user                                  # whoami (works; auth status output is misleading)
glab api user/keys                             # NOT user/ssh_keys (404)
glab api events                                # your activity (glab user events fails here)
glab api "projects/:id/search?scope=blobs&search=TERM"   # code text search (semantic search needs a paid tier)
```

## Failure patterns

| Symptom | Meaning | Action |
|---|---|---|
| "None of the git remotes correspond to GITLAB_HOST" | Gateway host mismatch (by design) | Use `glab api`; never change config |
| HTTP 304 | Already subscribed / already done | Success — idempotent, not an error |
| HTTP 404 on `glab api graphql` or `work-items` | Gateway is REST-only | Use the REST equivalent |
| HTTP 403 on iterations/epics/analytics | Paid-tier feature | Report the limitation; no workaround |
| HTTP 422 on release create | Tag not on remote | Add `-f ref=main` |
| HTTP 422 on `changelog generate` | Commits lack required trailers | Report; no workaround |
| HTTP 404 on milestone DELETE | Endpoint doesn't support DELETE | `PUT` with `state_event=close` |
| HTTP 502 | Transient upstream error | Retry once after a few seconds |
| "Host key verification failed" | SSH attempted; no SSH keys exist | HTTPS URLs only |
| Command hangs | Interactive prompt waiting for input | Re-run with the non-interactive flag (`--yes`, `--clone=false`) |
| "Accepts 1 arg(s), received 2" or "Unknown flag" | Wrong syntax | Run `glab <cmd> --help`, correct, retry once |
| `glab auth status` says not authenticated | Cosmetic — auth works via pre-set token | Ignore; never run `glab auth login` |
