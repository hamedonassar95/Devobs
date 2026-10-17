#!/usr/bin/env bash
set -euo pipefail

# Infer current lifecycle phase for a feature by checking doc state.
# Usage: check-status.sh <feature-name>

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <feature-name>"
  exit 1
fi

FEATURE="$1"
AI_DEVKIT_BIN="${AI_DEVKIT_BIN:-npx ai-devkit@latest}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"
DOCS_ROOT="$(node -e '
const fs = require("node:fs");
const file = process.argv[1];
if (!fs.existsSync(file)) {
  process.stdout.write("docs/ai");
} else {
  try {
    const config = JSON.parse(fs.readFileSync(file, "utf8"));
    if (!Object.prototype.hasOwnProperty.call(config, "paths")) {
      process.stdout.write("docs/ai");
    } else if (!config.paths || typeof config.paths !== "object" || Array.isArray(config.paths)) {
      throw new Error("paths must be an object");
    } else if (!Object.prototype.hasOwnProperty.call(config.paths, "docs")) {
      process.stdout.write("docs/ai");
    } else if (typeof config.paths.docs !== "string" || !config.paths.docs.trim()) {
      throw new Error("paths.docs must be a non-empty string when provided");
    } else {
      process.stdout.write(config.paths.docs.trim());
    }
  } catch (error) {
    console.error(`Error: cannot read paths.docs from ${file}: ${error.message}`);
    process.exit(1);
  }
}
' "$REPO_ROOT/.ai-devkit.json")"
DOCS_ROOT="${DOCS_ROOT#./}"
DOCS_ROOT="${DOCS_ROOT%/}"
[[ "$DOCS_ROOT" == "." ]] && DOCS_ROOT=""

if [[ ! "$FEATURE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Error: feature name must contain only letters, digits, hyphens, and underscores"
  exit 1
fi

exists() { [[ -f "$1" ]]; }

LINT_OUTPUT="$($AI_DEVKIT_BIN lint --feature "$FEATURE" 2>/dev/null || true)"

lint_doc() {
  local phase="$1"
  awk -v phase="$phase" -v feature="$FEATURE" -v root="$DOCS_ROOT" '
    /^Feature: / { in_feature = ($0 == "Feature: " feature); next }
    /^Git:/ { in_feature = 0 }
    in_feature {
      path = $0
      sub(/^[[:space:]]*[^[:space:]]+[[:space:]]+/, "", path)
      prefix = (root == "" ? "" : root "/") phase "/"
      if (index(path, prefix) == 1 && path ~ /\.md$/) {
        print path
        exit
      }
    }
  ' <<< "$LINT_OUTPUT"
}

REQ="$(lint_doc requirements)"
DES="$(lint_doc design)"
PLN="$(lint_doc planning)"
IMP="$(lint_doc implementation)"
TST="$(lint_doc testing)"

if [[ -z "$REQ" || -z "$DES" || -z "$PLN" || -z "$IMP" || -z "$TST" ]]; then
  echo "Error: could not resolve feature docs from 'ai-devkit lint --feature $FEATURE'"
  echo "Run: $AI_DEVKIT_BIN lint --feature $FEATURE"
  exit 1
fi

echo "=== Status: $FEATURE ==="

# Check which docs exist
for doc in "$REQ" "$DES" "$PLN" "$IMP" "$TST"; do
  if exists "$doc"; then
    echo "[EXISTS] $doc"
  else
    echo "[MISS]   $doc"
  fi
done

# Count planning tasks if planning doc exists
if exists "$PLN"; then
  TOTAL=$(grep -Ec '^[[:space:]]*- \[[ xX]\][[:space:]]+' "$PLN" 2>/dev/null || true)
  DONE=$(grep -Ec '^[[:space:]]*- \[[xX]\][[:space:]]+' "$PLN" 2>/dev/null || true)
  TOTAL=${TOTAL:-0}
  DONE=${DONE:-0}
  TODO=$((TOTAL - DONE))
  echo ""
  echo "Planning: $DONE/$TOTAL tasks done, $TODO remaining"
fi

phase_complete() {
  local phase="$1"
  grep -Eiq "^[[:space:]]*-[[:space:]]+\\[[xX]\\][[:space:]]+Phase[[:space:]]+$phase([[:space:]:.-]|$)" "$IMP"
}

# Infer phase. Required documents and the post-review planning gate block
# forward progress until their completion markers are recorded. Later phase
# completion is persisted so resumes do not repeat completed work.
echo ""
echo "--- Suggested phase ---"
if ! exists "$REQ"; then
  echo "Phase 1 (New Requirement) — no requirements doc yet"
elif ! exists "$IMP"; then
  echo "No phase suggested: required implementation document is missing: $IMP"
  echo "Restore it from the configured phase template before continuing."
  exit 1
elif ! grep -Fq '## Lifecycle progress' "$IMP"; then
  echo "Phase 2 (Review Requirements) — initialize the lifecycle progress checklist in $IMP"
elif ! phase_complete 2; then
  echo "Phase 2 (Review Requirements) — requirements review is not recorded as complete"
elif ! exists "$DES"; then
  echo "Phase 3 (Review Design) — no design document yet"
elif ! phase_complete 3; then
  echo "Phase 3 (Review Design) — design review is not recorded as complete"
elif ! exists "$TST"; then
  echo "No phase suggested: required testing document is missing: $TST"
  echo "Restore it from the configured phase template before continuing."
  exit 1
elif ! phase_complete 4; then
  echo "Phase 4 (Create Initial Plan) — create the plan after requirements and design reviews"
elif ! exists "$PLN"; then
  echo "Phase 4 (Create Initial Plan) — design exists but no planning doc"
elif [[ ${TOTAL:-0} -eq 0 ]]; then
  echo "Phase 4 (Create Initial Plan) — no planning tasks recorded"
elif [[ ${TODO:-0} -gt 0 ]]; then
  echo "Phase 5 (Execute Plan) — $TODO tasks remaining"
elif ! phase_complete 7; then
  echo "Phase 7 (Check Implementation) — all tasks done, verify against design"
elif ! phase_complete 8; then
  echo "Phase 8 (Write Tests) — implementation check is complete"
elif ! phase_complete 9; then
  echo "Phase 9 (Code Review) — testing is complete"
else
  echo "Lifecycle complete — phases 7, 8, and 9 are recorded as complete"
fi
