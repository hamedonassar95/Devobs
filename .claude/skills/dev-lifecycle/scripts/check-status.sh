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

if [[ ! "$FEATURE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Error: feature name must contain only letters, digits, hyphens, and underscores"
  exit 1
fi

exists() { [[ -f "$1" ]]; }

LINT_OUTPUT="$($AI_DEVKIT_BIN lint --feature "$FEATURE" 2>/dev/null || true)"

lint_doc() {
  local phase="$1"
  awk -v phase="$phase" -v feature="$FEATURE" '
    /^Feature: / { in_feature = ($0 == "Feature: " feature); next }
    /^Git:/ { in_feature = 0 }
    in_feature {
      line = $0
      sub(/^[[:space:]]*[^[:space:]]+[[:space:]]+/, "", line)
      count = split(line, fields, /[[:space:]]+/)
      path = fields[count]
      if (path ~ ("/" phase "/") && path ~ /\.md$/) {
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
  TOTAL=$(grep -Ec '^[[:space:]]*- \[' "$PLN" 2>/dev/null || true)
  DONE=$(grep -Ec '^[[:space:]]*- \[x\]' "$PLN" 2>/dev/null || true)
  TOTAL=${TOTAL:-0}
  DONE=${DONE:-0}
  TODO=$((TOTAL - DONE))
  echo ""
  echo "Planning: $DONE/$TOTAL tasks done, $TODO remaining"
fi

# Infer phase. Required documents gate forward progress; phase completion after
# implementation is persisted in the implementation document so resumes do not
# keep returning to Phase 7.
echo ""
echo "--- Suggested phase ---"
if ! exists "$REQ"; then
  echo "Phase 1 (New Requirement) — no requirements doc yet"
elif ! exists "$DES"; then
  echo "Phase 1 (New Requirement) — requirements exist but no design doc"
elif ! exists "$TST"; then
  echo "No phase suggested: required testing document is missing: $TST"
  echo "Restore it from the configured phase template before continuing."
  exit 1
elif ! exists "$PLN"; then
  echo "Phase 4 (Create Initial Plan) — design exists but no planning doc"
elif ! exists "$IMP"; then
  echo "No phase suggested: required implementation document is missing: $IMP"
  echo "Restore it from the configured phase template before continuing."
  exit 1
elif [[ ${TOTAL:-0} -eq 0 ]]; then
  echo "Phase 4 (Create Initial Plan) — no planning tasks recorded"
elif [[ ${TODO:-0} -gt 0 ]]; then
  echo "Phase 5 (Execute Plan) — $TODO tasks remaining"
elif ! grep -Fq '## Lifecycle progress' "$IMP"; then
  echo "Phase 7 (Check Implementation) — all tasks done; initialize the lifecycle progress checklist in $IMP"
elif ! grep -Eiq '^[[:space:]]*-[[:space:]]+\[[xX]\][[:space:]]+Phase[[:space:]]+7([[:space:]:.-]|$)' "$IMP"; then
  echo "Phase 7 (Check Implementation) — all tasks done, verify against design"
elif ! grep -Eiq '^[[:space:]]*-[[:space:]]+\[[xX]\][[:space:]]+Phase[[:space:]]+8([[:space:]:.-]|$)' "$IMP"; then
  echo "Phase 8 (Write Tests) — implementation check is complete"
elif ! grep -Eiq '^[[:space:]]*-[[:space:]]+\[[xX]\][[:space:]]+Phase[[:space:]]+9([[:space:]:.-]|$)' "$IMP"; then
  echo "Phase 9 (Code Review) — testing is complete"
else
  echo "Lifecycle complete — phases 7, 8, and 9 are recorded as complete"
fi
