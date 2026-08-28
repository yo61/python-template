# Lockfile sync preconditions

## Decision: gate `sync-lockfile` on an open Release PR, not on release-please's `prs` output

`.github/workflows/release.yaml` resolves the Release PR by its
`autorelease: pending` label and runs whenever one exists, rather than only
when release-please reported a created or updated PR. CI moves from
`uv sync --frozen` to `--locked`, and `tool.uv.required-version` in
`pyproject.toml` becomes the single source for the uv version.

## Context: why it came up

Porting `sync-lockfile` into `yo61/gh-release-stats` (2026-08-28) put a review
on the job for the first time. `release-please`'s `prs` output is set only when
the action actually updated a pull request, and
`maybeUpdateExistingPullRequest` (`src/manifest.ts`, v17.6.0) declines to
update when the regenerated body is unchanged. A push carrying only hidden
commit types — `chore`, `ci`, `docs`, `style`, `refactor`, `test`, `build` —
therefore reports nothing.

That made the job non-idempotent. A sync missed once was never retried until
the next releasable commit. The case was not hypothetical: gh-release-stats had
an open Release PR with a stale lockfile precisely because the job did not yet
exist, and merging the job under the old gate — itself a `ci:` commit — would
not have repaired it.

## Alternatives considered

- **Keep the `prs` gate.** It works for every ordinary release, because a
  version bump always rewrites the changelog and so always changes the PR body.
  Four clean releases in `yo61/unifictl` came through it. Rejected: it is right
  by coincidence, and silently wrong in exactly the recovery case where the job
  matters most.
- **`always-update` on release-please.** Reachable: it is a documented key of
  `release-please-config.json` (`schemas/config.json`, read at
  `src/manifest.ts:1471`), which this workflow already passes. It would make
  the `prs` output unconditional and the old gate correct. Rejected for what
  it costs instead: `alwaysUpdate` routes to `updateExistingPullRequest`, which
  rewrites the Release branch on *every* push to `main`. That discards the
  synced lockfile commit and re-adds it each time, and with `uv sync --locked`
  it puts the Release PR's required checks red on every push rather than only
  on a version change.
- **`gh pr list --label 'autorelease: pending'`.** Rejected after checking with
  `GH_DEBUG=api`: `--label` resolves through `query PullRequestSearch`, the
  search API, which is index-lagged and can miss a PR created seconds earlier
  in the preceding job. Listing unfiltered hits `repository.pullRequests` and
  is read-your-writes; the label is matched locally in `jq`.

## Reasoning

"Did release-please just update a PR?" is a proxy. "Is there an open Release PR
whose lockfile might be stale?" is the job's actual precondition. Asking the
real question makes the job idempotent — it re-runs until the lockfile is in
sync and exits quietly once it is — and removes the dependence on release-please
having something new to say.

`--locked` is the same class of error one layer up: `--frozen` installs from
the lockfile without checking that it is current, so drift merged silently and
this job was the only detector. `--locked` asserts freshness and fails the PR.

## Trade-offs accepted

- Selecting by label alone would let anyone with write access choose the
  branch a `uv lock` runs on. Mitigated by also requiring the release App as
  author and a `release-please--branches--` head branch, and by keeping the
  App token out of the step that runs `uv lock` — but the selector is now
  three conditions that must stay in step with release-please's defaults.
- The job now runs on every push to `main` — a token mint and one API call —
  instead of skipping cheaply. That is the price of idempotence.
- It depends on release-please's default labelling. Either `skip-labeling` or
  a custom `label` in `release-please-config.json` breaks the lookup, and the
  job would report success having synced nothing.
- Release PRs show one failing CI run between release-please pushing the
  version bump and `sync-lockfile` committing the lockfile.
- `required-version` makes uv upgrades a deliberate `pyproject.toml` edit;
  Dependabot does not update that key.

## Supersedes

Nothing. Complements the reasoning documented in
`docs/site/content/docs/explanation/releases.mdx`.
