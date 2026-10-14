# uv.lock revision flapping

## Decision: accept the `revision` flip in `uv.lock` until Dependabot ships uv 0.12.22+

Dependabot PRs set `uv.lock` to `revision = 3`; Release PRs set it back to
`revision = 5`. Merge both as they come. A `revision` line change in either is
expected and is not a reason to hold a PR or push a relock commit to it.

## Context: why it came up

Reviewing #60 and #64 (2026-10-14) showed both downgrading `revision = 5` to
`3`. The history shows the same flip in #36, #45 and #53.

- uv 0.12.22 moved the lock format to revision 5. Re-locking the same tree
  with each version from 0.12.18 to 0.12.22 (version bump forced, so the lock
  is rewritten) gave 3 for 0.12.18–0.12.21 and 5 for 0.12.22.
- A `uv lock` with nothing to change leaves the existing revision alone; only a
  rewrite stamps the running uv's revision. A plain relock therefore looks like
  a fix and is not one.
- Dependabot uses its own uv, `uv==0.12.18` in
  `dependabot-core/uv/helpers/requirements.txt`, and never reads
  `tool.uv.required-version`.
- The `sync-lockfile` job in `release.yaml` installs the newest uv in
  `required-version` (0.12.24 on the 0.1.5 Release PR), and the version bump
  forces a rewrite.

Both revisions pass `uv sync --locked`. The cost is one unrelated line in
every Dependabot and Release PR diff.

## Alternatives considered

- **Raise `required-version` to `>=0.12.22`.** Rejected: Dependabot's uv
  0.12.18 would refuse to run, failing every Python Dependabot PR.
- **A CI job that relocks Dependabot branches with the project's uv.**
  Rejected: it runs `uv lock`, which executes build backends, on a branch it
  must then push to, so the token and the untrusted tree meet in one job.
  `2026-08-28-lockfile-sync-preconditions.md` keeps those apart on purpose.
  Too much exposure for a cosmetic diff.
- **Move Python updates from Dependabot to Renovate.** Renovate already runs
  here for other managers. Rejected as a fix for this alone; worth revisiting
  only if Dependabot is being dropped for other reasons.

## Reasoning

The flip is harmless and has an upstream end date: dependabot-core has open
uv bumps (#16457 to 0.12.20, #16458 to the 0.12.22 image) and bumps uv
regularly. Every local fix either breaks Dependabot or widens the release
token's exposure.

## Trade-offs accepted

- Dependabot and Release PRs carry a `revision` line change until upstream
  catches up.
- The same thing will recur at the next uv lock-format change, whenever
  Dependabot lags uv. Check this record before investigating again.
- Revisit if the flip continues after dependabot-core ships uv 0.12.22 or
  later; the cause would then be something else.

## Supersedes

Nothing.
