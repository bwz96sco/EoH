#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AST_DIR="${ABCODER_AST_DIR:-$HOME/.asts}"

if (($# > 0)); then
  TARGETS=("$@")
else
  TARGETS=(
    "eoh/src/eoh"
    "examples/user_abr"
  )
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd npx
require_cmd abcoder

cd "$ROOT_DIR"

GITNEXUS_ARGS=("gitnexus" "analyze")
if [[ -f ".gitnexus/meta.json" ]] && command -v jq >/dev/null 2>&1; then
  if jq -e '.stats.embeddings > 0' ".gitnexus/meta.json" >/dev/null 2>&1; then
    GITNEXUS_ARGS+=("--embeddings")
  fi
fi

echo "Refreshing GitNexus index..."
npx "${GITNEXUS_ARGS[@]}"

mkdir -p "$AST_DIR"

for target in "${TARGETS[@]}"; do
  rel_target="${target#./}"
  abs_target="$(cd "$rel_target" && pwd)"
  output_name="$(printf '%s' "$rel_target" | tr '/:' '__')"
  output_file="$AST_DIR/${output_name}.json"

  echo "Refreshing ABCoder AST: $abs_target -> $output_file"
  abcoder parse python "$abs_target" -o "$output_file"
done

echo "Code intelligence refresh complete."
echo "Next: use list_repos() or 'abcoder list-repos' to confirm the repo names now exposed by ABCoder MCP."
