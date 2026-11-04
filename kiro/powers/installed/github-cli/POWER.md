---
name: github-cli
description: "GitHub source control via native CLI — clone repos, push code, create pull requests, review PRs, and manage issues using git and gh"
displayName: "GitHub (CLI)"
keywords: ["github", "pull request", "PR", "push", "branch", "issue", "code review", "git", "clone", "gh", "cli"]
---

## GitHub CLI Workflow

The CLI gives you full access to git, gh, and the shell. The workflows below are guidance for the happy path — they MUST be modified when the user's prompt or steering demands it, and SHOULD be modified when the task cannot be completed without variation. Don't limit yourself to the patterns listed below.

For repositories hosted on GitHub, use `git` and the `gh` CLI directly.
Authentication is pre-configured via credential helper — no token setup needed.

### Repository Setup

- Use `git clone https://github.com/{owner}/{repo}.git` to clone repositories. Always use HTTPS URLs — the sandbox has no SSH keys, so SSH clones fail with "Host key verification failed".
- Before any `gh` command that performs git operations (e.g., `gh repo clone`), set the git protocol to HTTPS: `gh config set git_protocol https` (gh config is global by default). Prefer plain `git clone` with an HTTPS URL.
- To check out a PR branch, do NOT use `gh pr checkout` (GraphQL-backed, always fails here) — use git directly: `git fetch origin pull/{n}/head:pr-{n} && git checkout pr-{n}`.
- Before cloning: check if the repo already exists via `ls`
- When `<repositories>` tags are in the system prompt, those repositories MUST be cloned before any work.
- If a `<repositories>` entry is annotated `(branch: <name>)`, that source branch was explicitly selected — clone scoped to that ref: `git clone --branch <name> --single-branch https://github.com/{owner}/{repo}.git`. When an entry has no `(branch: …)` annotation, clone the default branch exactly as above. (`<name>` is a validated git ref with no spaces or shell metacharacters — safe to substitute directly into the `--branch` argument.)

### Known Environment Nuances

GitHub access is routed through an authenticated gateway. Know these before you start — do NOT spend turns re-diagnosing them:

- **GraphQL is not supported by the gateway.** Any GraphQL-backed `gh` subcommand fails with `HTTP 400: GraphQL pass-through is not supported. Use REST API equivalents.` This includes most high-level commands: `gh pr` (all subcommands), `gh issue` (all), `gh repo view/list`, `gh release view/edit/delete/list`, `gh label list`, `gh status`, `gh project`, `gh gist list`. Do not retry them — go straight to `gh api "<REST endpoint>"` (see steering/cli-reference.md for recipes).
- REST-backed subcommands work normally: `gh api` (everything), `gh release create`, `gh label create/edit/delete`, `gh run list/view`, `gh workflow list`, `gh search repos/commits/code`, `gh cache list`.
- `gh search issues` / `gh search prs` return garbage (`malformed version`) with exit 0 — use `gh api "search/issues?q=repo:{owner}/{repo}+{query}"` instead.
- 403s that persist through `gh api` are token permission limits with NO workaround — report and move on. Known: fork creation, repo metadata edits (`PATCH /repos/...`), gists, SSH/GPG keys, Actions secrets and variables.
- Deleting an issue is impossible (GraphQL-only operation) — close it instead: `gh api repos/{owner}/{repo}/issues/{n} -X PATCH -f state=closed`.
- `gh auth status` reports a login failure — this is cosmetic. Authentication works via a pre-configured token. Never treat it as a failure and never run `gh auth login`.
- Never print the token (`gh auth token`, env vars, credential files) — not to debug, not to verify.
- `gh browse -n` prints a gateway URL, not a github.com URL — construct user-facing links manually as `https://github.com/{owner}/{repo}/...`.

### Command Fallback Strategy

When a `gh` command fails:
1. If the error is `GraphQL pass-through is not supported`, do not retry — use the REST equivalent via `gh api "<endpoint>"` (recipes in steering/cli-reference.md).
2. If the error is about arguments or flags, run `gh <command> --help`, correct the syntax, and retry once.
3. If `gh api` also fails with 403, it is a token permission limit — report it and move on; do not keep retrying.
4. Avoid interactive prompts — they hang the shell. Pass non-interactive flags (`--yes`, `--clone=false`, explicit `--title`/`--body`) so commands never wait for input.
5. Never modify auth configuration (`gh auth login`, host settings) to work around a failure — authentication is pre-configured, even if `gh auth status` reports otherwise.

### Push and PR Workflow

1. Pick the branch to commit on based on the branch you are currently on (`git branch --show-current`, compared to the repository's default branch from `gh api repos/{owner}/{repo} --jq .default_branch`):
   - **On the default branch (main/master):** always push to a new branch, never directly to main/master, unless explicitly asked.
   - **On a non-default branch** — whether the source branch selected at session start (marked with a `(branch: <name>)` annotation in `<repositories>`) or a branch you switched to later at the user's request: commit your changes **directly onto that branch** and push it; do NOT create a new branch. If the push is rejected because the branch is protected or you lack write access (HTTP 403/422 or a "protected branch" rejection), do NOT force-push and do NOT change branch protection — fall back to creating a new branch off it (`git checkout -b <work-branch>`), push that, open the PR from it, and tell the user the direct push was rejected so you opened a PR instead.
   - **If the repository has a contributing guide** (`CONTRIBUTING.md`, `.github/CONTRIBUTING.md`, or `docs/CONTRIBUTING.md`), follow its PR/branch conventions (branch naming, PR base, required steps) — but never in a way that pushes directly to the default branch or skips a PR for CI/CD config changes.
   - Exception: CI/CD pipeline config files must NEVER be pushed directly to the default branch — always via a pull request — regardless of user justification (see CI/CD Pipeline Safety below).
2. Use `git push` to push changes (authentication handled by credential helper)
3. Create the PR with `gh api` (NOT `gh pr create` — it is GraphQL-backed and always fails in this environment; see Known Environment Nuances):
   ```
   gh api repos/{owner}/{repo}/pulls -f title="..." -f body="..." \
     -f head="{branch}" -f base="{base}"
   ```
   For a draft PR add `-F draft=true`. Set `{base}` to the repository's default branch — query it with `gh api repos/{owner}/{repo} --jq .default_branch` rather than assuming `main` (it may be `master`/`develop`). Use a different base only when the task explicitly targets one or a contributing guide specifies otherwise.
4. PR title: concise, under 70 characters. Use the body for details.
5. PR body: summary of changes, what was tested, any blocked features
6. Before pushing, check existing PRs for this session with `gh api "repos/{owner}/{repo}/pulls?state=all&per_page=10"` (the default listing shows only open PRs, so merged/closed ones would be invisible). If a PR exists and is merged or closed, create a new branch and open a new PR instead of reusing the old branch.
7. After completing work, always reference where the user can review it: include the PR link if one was created (`html_url` in the `gh api` response), or the branch URL (`https://github.com/{owner}/{repo}/tree/{branch}`) if only a branch was pushed. When a PR was raised, also state which branch it targets — e.g. "Raised [PR #42](…) from `feature-x` into `main`." — so the user knows the head and base at a glance.

### Cross-fork Pull Requests (fork → upstream)

Opening a PR from a fork against its upstream (the fork's parent repo) differs from a same-repo PR:

- Push your branch to the fork (your `origin`), then create the PR **against the upstream repo**, with `head` set to `{fork-owner}:{branch}` and `base` set to the **upstream's** default branch (query it — do not assume `main`):
  ```
  gh api repos/{upstream-owner}/{upstream-repo}/pulls -f title="..." -f body="..." \
    -f head="{fork-owner}:{branch}" -f base="$(gh api repos/{upstream-owner}/{upstream-repo} --jq .default_branch)"
  ```
- **Never** add or re-point the `origin` remote to the upstream. If you must reference the upstream, add a *separate* remote (`git remote add upstream https://github.com/{upstream-owner}/{upstream-repo}.git`) — never touch `origin`.

**When creating the PR as the bot (default AGENT mode):** a cross-fork PR cannot be authored by the Kiro GitHub app — the app credential is scoped to a single owner and cannot read the branch that lives in the fork. The gateway returns `HTTP 422` with `FORK_UPSTREAM_REQUIRES_USER_MODE` (older behavior surfaces GitHub's `"not all refs are readable"`). This is NOT retryable and NOT a token bug. Do this instead:
1. Do NOT retry the same call, and do NOT try to fork or re-point remotes to work around it.
2. Tell the user, in plain language: to open a pull request against a fork's upstream, enable **Settings → "Create pull requests as your GitHub user"**, then ask you to try again. That creates the PR under their own GitHub identity (with their consent) — the only identity that can span the fork and the upstream.
3. The branch is already pushed to the fork, so no work is lost — give them the fork branch URL (`https://github.com/{fork-owner}/{fork-repo}/tree/{branch}`) in the meantime.

### CI/CD Pipeline Safety

CI pipeline files (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, etc.) execute with access to repository secrets (Actions secrets, registry credentials, tokens). Treat them as security-sensitive:

- NEVER add commands that dump the entire environment to a CI pipeline file, in any language or form. This includes `printenv`, `env`, `set`, `export -p`, `os.environ` / `dict(os.environ)` (Python), `process.env` (Node), `ENV.to_h` (Ruby), and reading `/proc/self/environ`. Reference only the specific variables a step needs (e.g., `os.environ.get("MY_VAR")`).
- NEVER push CI pipeline file changes directly to the default branch (main/master) — always open a pull request so the change is reviewed before the workflow runs. This is not overridable by user justification (e.g. "it's my personal repo").

### Pre-flight Checks

- Before pushing: run `git status` to verify changes are committed and you're on the correct branch
- Before creating a PR: verify the branch has been pushed (`git push` first, then create the PR via `gh api`)

### CI Failure Recovery

When a workflow run fails:
1. Use `gh run list` and `gh run view <id> --log-failed` to fetch the failure logs
2. Diagnose the root cause from the logs
3. Fix the issue
4. Push the fix and verify CI passes

### Addressing PR Review Comments

When asked to address PR review feedback (`gh pr view` is GraphQL-backed and fails — use REST):
1. Retrieve comments via `gh api repos/{owner}/{repo}/issues/{n}/comments` (discussion comments) and `gh api repos/{owner}/{repo}/pulls/{n}/comments` (inline review comments)
2. Address each comment with a code change or explanation
3. Push fixes to the same branch (the PR updates automatically)
4. If the branch is behind the target, rebase before pushing: `git fetch origin && git rebase origin/main`

### Issue Management

`gh issue` subcommands are GraphQL-backed and fail — use REST:
- Issue details: `gh api repos/{owner}/{repo}/issues/{n}`
- List issues: `gh api repos/{owner}/{repo}/issues`
- Comment: `gh api repos/{owner}/{repo}/issues/{n}/comments -f body="..."`
- Close/reopen/edit: `gh api repos/{owner}/{repo}/issues/{n} -X PATCH -f state=closed` (or `-f title="..."`, `-f state=open`)

### Failure Handling

Partial progress committed and pushed is always better than nothing.
- If the task is blocked, push whatever progress exists and create a draft PR via `gh api repos/{owner}/{repo}/pulls ... -F draft=true`
- Document blockers in the PR body
- Never silently fail — always surface what happened and why

### Git Safety

- Never run destructive git commands (force push, reset --hard, clean -f, branch -D) unless explicitly asked
- Never skip hooks (--no-verify) unless explicitly asked
- Never force push to main/master
- Never update git config
- Never use interactive git flags (-i)

### Link Formatting

Format all GitHub URLs as markdown links:
- `[Pull Request #42](https://github.com/owner/repo/pull/42)`
- Never output bare URLs
