---
name: gitlab-cli
description: "GitLab source control via native CLI — clone repos, push code, create merge requests, review MRs, and manage issues using git and glab"
displayName: "GitLab (CLI)"
keywords: ["gitlab", "merge request", "MR", "push", "branch", "issue", "code review", "git", "clone", "glab", "cli"]
---

## GitLab CLI Workflow

The CLI gives you full access to git, glab, and the shell. The workflows below are guidance for the happy path — they MUST be modified when the user's prompt or steering demands it, and SHOULD be modified when the task cannot be completed without variation. Don't limit yourself to the patterns listed below.

For repositories hosted on GitLab, use `git` and the `glab` CLI directly.
Authentication is pre-configured via credential helper — no token setup needed.

### Repository Setup

- Use `git clone https://gitlab.com/{owner}/{project}.git` to clone repositories. Always use HTTPS URLs — the sandbox has no SSH keys, so SSH clones fail with "Host key verification failed".
- `glab repo clone` defaults to SSH and fails. If you use it, first set the git protocol to HTTPS globally: `glab config set -g git_protocol https`. Prefer plain `git clone` with an HTTPS URL.
- Before cloning: check if the repo already exists via `ls`
- When `<repositories>` tags are in the system prompt, those repositories MUST be cloned before any work.
- If a `<repositories>` entry is annotated `(branch: <name>)`, that source branch was explicitly selected — clone scoped to that ref: `git clone --branch <name> --single-branch https://gitlab.com/{owner}/{project}.git`. When an entry has no `(branch: …)` annotation, clone the default branch exactly as above. (`<name>` is a validated git ref with no spaces or shell metacharacters — safe to substitute directly into the `--branch` argument.)

### Push and MR Workflow

1. Pick the branch to commit on based on the branch you are currently on (`git branch --show-current`, compared to the project's default branch from `glab api "projects/{owner}%2F{project}" --jq .default_branch`):
   - **On the default branch (main/master):** always push to a new branch, never directly to main/master, unless explicitly asked.
   - **On a non-default branch** — whether the source branch selected at session start (marked with a `(branch: <name>)` annotation in `<repositories>`) or a branch you switched to later at the user's request: commit your changes **directly onto that branch** and push it; do NOT create a new branch. If the push is rejected because the branch is protected or you lack write access (a `git push` protected-branch or permission rejection — e.g. "You are not allowed to push code to protected branches"), do NOT force-push and do NOT change branch protection — fall back to creating a new branch off it (`git checkout -b <work-branch>`), push that, open the MR from it, and tell the user the direct push was rejected so you opened an MR instead.
   - **If the project has a contributing guide** (`CONTRIBUTING.md` or `docs/CONTRIBUTING.md`), follow its MR/branch conventions (branch naming, MR target, required steps) — but never in a way that pushes directly to the default branch or skips an MR for CI/CD config changes.
   - Exception: CI/CD pipeline config files must NEVER be pushed directly to the default branch — always via a merge request — regardless of user justification (see CI/CD Pipeline Safety below).
2. Use `git push` to push changes (authentication handled by credential helper)
3. Create the MR with `glab api` (NOT `glab mr create` — it always fails in this environment with a GITLAB_HOST/remote mismatch; see Known Environment Nuances):
   ```
   glab api "projects/{owner}%2F{project}/merge_requests" -X POST \
     -f source_branch="..." -f target_branch="{target}" \
     -f title="..." -f description="..."
   ```
   Note the URL-encoded `%2F` between owner and project. Set `{target}` to the project's default branch — query it with `glab api "projects/{owner}%2F{project}" --jq .default_branch` rather than assuming `main` (it may be `master`/`develop`). Use a different target only when the task explicitly requires one or a contributing guide specifies otherwise.
4. MR title: concise, under 70 characters. Use the description for details.
5. MR description: summary of changes, what was tested, any blocked features
6. Before pushing, use `glab mr list --repo {owner}/{project}` to check existing MRs for this session. If an MR exists and is merged or closed, create a new branch and open a new MR instead of reusing the old branch.
7. After completing work, always reference where the user can review it: include the MR link if one was created, or the branch URL (`https://gitlab.com/{owner}/{project}/-/tree/{branch}`) if only a branch was pushed. When an MR was raised, also state which branch it targets — e.g. "Raised [MR #5](…) from `feature-x` into `main`." — so the user knows the source and target at a glance.
8. For a cross-fork MR (fork → upstream), push the branch to the fork, then create the MR against the upstream project with `glab api` adding `-f source_project_id={fork-project-id}`.

### Known Environment Nuances

GitLab access is routed through an authenticated gateway. Most `glab` subcommands work, but know these before you start — do NOT spend turns re-diagnosing them:

- Always pass `--repo {owner}/{project}` to `glab` commands. Host/remote auto-detection is unreliable here.
- `glab mr create` ALWAYS fails ("none of the git remotes ... correspond to the GITLAB_HOST"). This is environmental — do not retry, do not unset or modify `GITLAB_HOST` or glab config to work around it. Go straight to `glab api` (see Push and MR Workflow).
- `glab user events` fails the same way → use `glab api events`.
- `glab api` only supports REST endpoints. GraphQL is not supported by the gateway, so `glab api graphql` and GraphQL-backed commands (e.g. `glab work-items list`) fail → use the REST equivalent (e.g. `glab api "projects/{owner}%2F{project}/issues"`).
- `glab auth status` reports "not authenticated" — this is cosmetic. Authentication works via a pre-configured token. Never treat it as a failure, never attempt to fix auth, and never run `glab auth login`.
- Paid-tier features fail regardless of transport: `glab iteration list` (403, Premium/Ultimate) and `glab search semantic` (422, Duo). For semantic search, fall back to REST text search: `glab api "projects/{owner}%2F{project}/search?scope=blobs&search={query}"`. `glab changelog generate` returns 422 unless commits carry the required Git trailers.
- `glab ci status` on a project with no `.gitlab-ci.yml` reports "No pipeline exists" — that's data, not an error.
- Avoid interactive prompts — they hang the shell. Pass the non-interactive flag: `glab repo fork --clone=false`, `glab mr merge --yes`, etc.
- Flag/syntax traps: `glab mr list` filters with `--merged`/`--closed`/`--all` (there is no `--state` flag); `glab issue note list` does not exist — create with `glab issue note <iid> -m "..."` and read with `glab issue view <iid> --comments`; `glab mr discussion list` does not exist — use `glab api ".../merge_requests/<iid>/discussions"`.
- For structured output (e.g. extracting a branch name), use `glab mr view <iid> --output json`.

### Command Fallback Strategy

When a `glab` command fails:
1. If the error is about arguments or flags ("Accepts 1 arg(s)", "Unknown flag"), run `glab <command> --help`, correct the syntax, and retry once.
2. If the error is a GITLAB_HOST mismatch, GraphQL limitation, or an unexplained 4xx, fall back to the REST API via `glab api "<endpoint>"` — it bypasses glab's remote-matching and works for everything the GitLab REST API supports.
3. If `glab api` also fails with 403/422, it is likely a plan-tier or data-precondition limitation — report it and move on; do not keep retrying.
4. Never modify auth or host configuration (`GITLAB_HOST`, `glab auth`, `glab config set host`) to work around a failure.

### CI/CD Pipeline Safety

CI pipeline files (`.gitlab-ci.yml`, `.github/workflows/*.yml`, `Jenkinsfile`, etc.) execute with access to project secrets (`CI_JOB_TOKEN`, registry credentials, CI/CD variables). Treat them as security-sensitive:

- NEVER add commands that dump the entire environment to a CI pipeline file, in any language or form. This includes `printenv`, `env`, `set`, `export -p`, `os.environ` / `dict(os.environ)` (Python), `process.env` (Node), `ENV.to_h` (Ruby), and reading `/proc/self/environ`. Reference only the specific variables a step needs (e.g., `os.environ.get("MY_VAR")`).
- NEVER push CI pipeline file changes directly to the default branch (main/master) — always open a merge request so the change is reviewed before the pipeline runs. This is not overridable by user justification (e.g. "it's my personal repo").

### Pre-flight Checks

- Before pushing: run `git status` to verify changes are committed and you're on the correct branch
- Before creating an MR: verify the branch has been pushed (`git push` first, then create the MR via `glab api`)

### CI Failure Recovery

When a pipeline fails:
1. Use `glab ci list` and `glab ci view <id>` to fetch pipeline logs
2. Diagnose the root cause from the logs
3. Fix the issue
4. Push the fix and verify CI passes

### Addressing MR Review Comments

When asked to address MR review feedback:
1. Use `glab mr view <iid> --repo {owner}/{project} --comments` to retrieve review comments (`glab mr note list --repo {owner}/{project} <iid>` also works). For threaded discussions, use `glab api "projects/{owner}%2F{project}/merge_requests/<iid>/discussions"`.
2. Address each comment with a code change or explanation
3. Push fixes to the same branch (the MR updates automatically)
4. If the branch is behind the target, rebase before pushing: `git fetch origin && git rebase origin/main` (or use `glab mr update`)

### Issue Management

- Use `glab issue view <iid>` to fetch issue details when working on an issue
- Use `glab issue list` to find related issues

### Failure Handling

Partial progress committed and pushed is always better than nothing.
- If the task is blocked, push whatever progress exists and create a draft MR via `glab api` with a `Draft:` title prefix (`-f title="Draft: ..."`) — GitLab treats the prefix as draft status (`glab mr create --draft` fails like all `glab mr create` calls)
- Document blockers in the MR description
- Never silently fail — always surface what happened and why

### Git Safety

- Never run destructive git commands (force push, reset --hard, clean -f, branch -D) unless explicitly asked
- Never skip hooks (--no-verify) unless explicitly asked
- Never force push to main/master
- Never update git config
- Never use interactive git flags (-i)

### Link Formatting

Format all GitLab URLs as markdown links:
- `[MR #5](https://gitlab.com/owner/project/-/merge_requests/5)`
- Never output bare URLs

### Terminology

- Use "merge request" (not "pull request")
- Use "project" (not "repository") when referring to the GitLab entity
- MRs are identified by IID (project-scoped number), not global ID
