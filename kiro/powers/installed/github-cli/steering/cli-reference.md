# gh CLI Reference — Gateway Environment

On-demand reference for working with `gh` in this environment. Read this when a
`gh` command fails or you need a REST API recipe. The happy-path workflow lives
in POWER.md; this file explains *why* commands fail and gives the exact fallbacks.

## Why gh subcommands fail here (read this first)

GitHub traffic routes through an authenticated gateway that supports the REST
API only. Most high-level `gh` subcommands (`pr`, `issue`, `repo view`,
`status`, …) are implemented on GitHub's GraphQL API, so they fail with:

> HTTP 400: GraphQL pass-through is not supported. Use REST API equivalents.

This is environmental and deterministic — retrying, changing flags, or touching
auth config will never fix it. Go straight to `gh api` with the REST endpoint.

**Never work around failures by changing configuration.** Do NOT run
`gh auth login`, do NOT change host settings, and never print token values
(`gh auth token`, env vars, credential files) — not to debug, not to verify.

## gh api — the universal fallback

`gh api` calls the GitHub REST API directly and works for everything the REST
API supports (with the token-permission exceptions listed below).

```bash
gh api <endpoint> [-X METHOD] [-f key=value]... [-F key=typed-value]...
```

- Methods: GET (default), `-X POST` (create), `-X PATCH` (update), `-X PUT`, `-X DELETE`
- `-f` sends string fields; `-F` sends typed fields (booleans/numbers, e.g. `-F draft=true`)
- Query params go in the URL: `gh api "repos/{owner}/{repo}/pulls?state=closed&per_page=100"`
- Pagination: default page size is 30; add `per_page=100` and `page=N` for more
- Custom media types via header, e.g. a PR diff: `-H "Accept: application/vnd.github.v3.diff"`

## Verified command matrix

Every command below was tested end-to-end in a sandbox session.

### Works natively (REST-backed) — use directly

| Command | Notes |
|---|---|
| `git clone/checkout/add/commit/push/branch` | full git protocol works |
| `gh api <anything>` | the universal path |
| `gh release create` | works (view/edit/delete/list do NOT — GraphQL) |
| `gh label create` / `edit` / `delete` | work (list does NOT — GraphQL) |
| `gh run list` / `gh run view <id>` | REST-backed |
| `gh workflow list` | REST-backed (`view` needs an explicit workflow argument) |
| `gh search repos` / `commits` / `code` | REST-backed |
| `gh cache list`, `gh repo deploy-key list` | REST-backed |
| `gh alias list`, `gh extension list` | local, no network |

### Fails with GraphQL 400 — use the gh api recipe

| Failing command | REST recipe |
|---|---|
| `gh pr create` | `gh api repos/{o}/{r}/pulls -f title="..." -f body="..." -f head={branch} -f base=<default>` (set `<default>` from `gh api repos/{o}/{r} --jq .default_branch`, not `main`; add `-F draft=true` for draft) |
| `gh pr list` | `gh api repos/{o}/{r}/pulls` (add `?state=all` for closed/merged) |
| `gh pr view <n>` | `gh api repos/{o}/{r}/pulls/{n}` |
| `gh pr diff <n>` | `gh api repos/{o}/{r}/pulls/{n} -H "Accept: application/vnd.github.v3.diff"` |
| `gh pr comment <n>` | `gh api repos/{o}/{r}/issues/{n}/comments -f body="..."` |
| `gh pr edit <n>` | `gh api repos/{o}/{r}/pulls/{n} -X PATCH -f title="..."` |
| `gh pr close <n>` / `reopen` | `gh api repos/{o}/{r}/pulls/{n} -X PATCH -f state=closed` (or `state=open`) |
| `gh pr merge <n>` | `gh api repos/{o}/{r}/pulls/{n}/merge -X PUT -f merge_method=merge` |
| `gh pr review <n> --approve` | `gh api repos/{o}/{r}/pulls/{n}/reviews -f event=APPROVE -f body="..."` |
| `gh pr checkout <n>` | pure git, no API: `git fetch origin pull/{n}/head:pr-{n} && git checkout pr-{n}` |
| `gh pr checks <n>` | two steps — resolve the head SHA first: `SHA=$(gh api repos/{o}/{r}/pulls/{n} --jq '.head.sha')`, then `gh api repos/{o}/{r}/commits/$SHA/check-runs` |
| `gh issue create` | `gh api repos/{o}/{r}/issues -f title="..." -f body="..."` |
| `gh issue list` / `view <n>` | `gh api repos/{o}/{r}/issues` / `.../issues/{n}` |
| `gh issue comment <n>` | `gh api repos/{o}/{r}/issues/{n}/comments -f body="..."` |
| `gh issue edit/close/reopen <n>` | `gh api repos/{o}/{r}/issues/{n} -X PATCH -f title="..."` / `-f state=closed` / `-f state=open` |
| `gh issue delete <n>` | impossible via REST — close it instead (`-f state=closed`) |
| `gh repo view` / `gh repo list` | `gh api repos/{o}/{r}` / `gh api "users/{o}/repos?per_page=100"` |
| `gh release view/edit/delete/list` | `gh api repos/{o}/{r}/releases` (`/tags/{tag}` to resolve; then `.../releases/{id}` with `-X PATCH` / `-X DELETE`) |
| `gh label list` | `gh api repos/{o}/{r}/labels` |
| `gh gist list` | `gh api gists` |
| `gh status`, `gh pr status`, `gh issue status`, `gh project list` | no direct recipe — query the specific repos/issues you need via REST |
| `gh search issues` / `prs` (prints `malformed version`) | `gh api "search/issues?q=repo:{o}/{r}+{query}"` (append `+type:pr` for PRs) |

Useful repo-inspection endpoints: `.../branches`, `.../contributors`, `.../tags`,
`.../commits/{sha}`, `.../actions/runs`, `.../actions/workflows`.

### Fails with 403 in BOTH forms — token permission limit, no workaround

Report and move on; do not retry:

- Forking: `gh repo fork` and `POST .../forks`
- Repo metadata edits: `gh repo edit` and `PATCH /repos/{o}/{r}`
- Gists (create): `gh gist create` and `POST /gists`
- SSH/GPG keys: `gh ssh-key list`, `gh gpg-key list`, `user/keys`, `user/gpg_keys`
- Actions secrets & variables: `gh secret list`, `gh variable list`, `.../actions/secrets`, `.../actions/variables`

## Failure patterns at a glance

| Error | Meaning | Action |
|---|---|---|
| `HTTP 400 ... GraphQL pass-through is not supported` | command is GraphQL-backed | use the `gh api` recipe above |
| `HTTP 403: Github returned a client error` (persists via `gh api`) | token permission limit | report, move on |
| `HTTP 404: Github returned a client error` | resource genuinely doesn't exist | fix the path/id — routing is fine |
| `gh auth status` login failure | cosmetic | ignore; auth works |
| "Host key verification failed" | SSH attempted; no SSH keys exist | HTTPS URLs only; `gh config set git_protocol https` |
| `malformed version:` from `gh search issues/prs` | broken output path | use `gh api search/issues` |
