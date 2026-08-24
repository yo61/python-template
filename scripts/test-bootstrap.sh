#!/usr/bin/env bash
# Generate projects from the template and prove they work.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

run_case() {
  local name=$1
  shift
  local dir="$WORK/$name"

  git -C "$REPO_ROOT" archive HEAD | (mkdir -p "$dir" && tar -x -C "$dir")
  git -C "$dir" init -q
  git -C "$dir" add -A
  git -C "$dir" -c user.email=t@example.com -c user.name=t commit -qm "init"

  (cd "$dir" && ./bootstrap --defaults "$@") || fail "$name: bootstrap exited non-zero"

  # No placeholder may survive anywhere in the generated tree.
  local leaks
  leaks=$(grep -rIl --exclude-dir=.git --exclude-dir=node_modules \
    --exclude-dir=.venv -e 'pythontemplate' -e 'python-template' "$dir" || true)
  [[ -z "$leaks" ]] || fail "$name: placeholders survived in:
$leaks"

  [[ -d "$dir/src/my_tool" ]] || fail "$name: src/my_tool missing"
  [[ ! -e "$dir/bootstrap" ]] || fail "$name: bootstrap did not delete itself"
  [[ ! -e "$dir/.bootstrap-defaults" ]] || fail "$name: defaults file survived"
  [[ ! -e "$dir/docs/superpowers/specs/2026-08-24-python-template-rewrite-design.md" ]] \
    || fail "$name: template design docs leaked into the generated project"

  grep -q "basePath = process.env.BASE_PATH ?? '/my-tool'" \
    "$dir/docs/site/next.config.mjs" || fail "$name: Fumadocs basePath not rewritten"

  (cd "$dir" && uv sync --quiet && task dev:check) || fail "$name: task dev:check failed"

  if [[ "$name" = flat ]]; then
    # The Fumadocs basePath is the most breakage-prone placeholder in the
    # template: get it wrong and the deployed site 404s its own assets,
    # invisible until deployment. Prove the rewritten site actually builds,
    # not just that the string was rewritten. --frozen-lockfile matches
    # .github/workflows/docs.yaml, so this also proves the committed
    # pnpm-lock.yaml still works after bootstrap rewrites the tree.
    (cd "$dir/docs/site" && pnpm install --frozen-lockfile) \
      || fail "$name: pnpm install --frozen-lockfile failed for docs/site"
    (cd "$dir/docs/site" && pnpm build) || fail "$name: pnpm build failed for docs/site"
    [[ -f "$dir/docs/site/out/index.html" ]] \
      || fail "$name: docs/site/out/index.html missing after pnpm build"
  fi

  echo "PASS: $name"
}

run_case flat
run_case ddd --ddd

# The DDD case must additionally have layers and a passing contract.
DDD="$WORK/ddd"
for layer in application domain infrastructure; do
  [[ -d "$DDD/src/my_tool/$layer" ]] || fail "ddd: src/my_tool/$layer missing"
done
grep -q '^\[tool.importlinter\]' "$DDD/pyproject.toml" \
  || fail "ddd: importlinter block still commented out"
(cd "$DDD" && task dev:imports) || fail "ddd: import contracts broken"

echo "PASS: all bootstrap cases"
