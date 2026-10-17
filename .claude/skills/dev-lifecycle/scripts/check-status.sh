#!/usr/bin/env bash
set -euo pipefail

# Infer current lifecycle phase for a feature by checking doc state.
# Usage: check-status.sh <feature-name>

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <feature-name>"
  exit 1
fi

FEATURE="$1"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"
AI_DEVKIT_BIN="$(printenv AI_DEVKIT_BIN 2>/dev/null || true)"
AI_DEVKIT_PREFIX_ARGS=()
if [[ -z "$AI_DEVKIT_BIN" ]]; then
  AI_DEVKIT_BIN="npx"
  AI_DEVKIT_PREFIX_ARGS=(--yes ai-devkit@0.70.1)
fi

if [[ ! "$FEATURE" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Error: feature name must contain only letters, digits, hyphens, and underscores"
  exit 1
fi

exists() { [[ -f "$1" ]]; }

LINT_TMP_DIR="$(printenv TMPDIR 2>/dev/null || true)"
if [[ -z "$LINT_TMP_DIR" ]]; then
  LINT_TMP_DIR="/tmp"
fi
LINT_STDERR_FILE="$(mktemp "$LINT_TMP_DIR/ai-devkit-status.XXXXXX")"
trap 'rm -f "$LINT_STDERR_FILE"' EXIT

LINT_STATUS=0
if LINT_OUTPUT="$("$AI_DEVKIT_BIN" "${AI_DEVKIT_PREFIX_ARGS[@]}" lint --json --feature "$FEATURE" 2>"$LINT_STDERR_FILE")"; then
  :
else
  LINT_STATUS=$?
fi

if DOC_PATHS="$(
  LINT_JSON="$LINT_OUTPUT" LINT_STATUS="$LINT_STATUS" FEATURE="$FEATURE" \
    node -e '
      const fs = require("node:fs");
      const path = require("node:path");
      const data = JSON.parse(process.env.LINT_JSON);
      const phases = ["requirements", "design", "planning", "implementation", "testing", "deployment", "monitoring"];
      const docCheckIds = new Set(phases.map((phase) => "feature-doc-" + phase));
      const checks = data.checks;
      const status = Number(process.env.LINT_STATUS);
      if (!Array.isArray(checks) || data.feature?.raw !== process.env.FEATURE ||
          typeof data.feature?.normalizedName !== "string" || !data.feature.normalizedName) {
        throw new Error("AI DevKit JSON does not describe the requested feature");
      }

      const expectedMiss = (check) =>
        check.category === "feature-docs" &&
        docCheckIds.has(check.id) &&
        check.level === "miss" && check.required === true;
      const expectedMisses = checks.filter(expectedMiss);
      const unexpectedMisses = checks.filter((check) => check.level === "miss" && !expectedMiss(check));
      const validLevels = checks.every((check) => ["ok", "miss", "warn"].includes(check.level));
      const expectedSuccess = status === 0 && data.pass === true && data.exitCode === 0 &&
        data.summary?.requiredFailures === 0 &&
        expectedMisses.length === 0 && unexpectedMisses.length === 0 && validLevels;
      const expectedMissingDocs = status !== 0 && data.pass === false && data.exitCode === status &&
        expectedMisses.length > 0 && data.summary?.requiredFailures === expectedMisses.length &&
        unexpectedMisses.length === 0 && validLevels;
      if (!expectedSuccess && !expectedMissingDocs) {
        throw new Error("AI DevKit lint failed for an unexpected reason");
      }

      const paths = phases.map((phase) => {
        const matchingChecks = checks.filter((item) => item.id === "feature-doc-" + phase);
        if (matchingChecks.length !== 1) {
          throw new Error("AI DevKit did not return exactly one " + phase + " document check");
        }
        const check = matchingChecks[0];
        if (check.category !== "feature-docs" || !["ok", "miss"].includes(check.level) ||
            typeof check.required !== "boolean" || (check.level === "miss" && !expectedMiss(check)) ||
            typeof check.message !== "string" || !check.message.trim() || /[\t\r\n]/.test(check.message)) {
          throw new Error("AI DevKit did not return a usable " + phase + " document path");
        }
        const pathSegments = check.message.split(/[\\/]/);
        const pathFromRoot = path.relative(process.cwd(), path.resolve(check.message));
        if (pathSegments.includes("..") || path.isAbsolute(check.message) || pathFromRoot === ".." ||
            pathFromRoot.startsWith(".." + path.sep) || path.basename(path.dirname(check.message)) !== phase ||
            path.extname(check.message) !== ".md") {
          throw new Error("AI DevKit returned a path outside the " + phase + " document directory");
        }
        if (check.level === "miss" && fs.existsSync(check.message)) {
          throw new Error("AI DevKit reports an existing " + phase + " document as missing");
        }
        if (check.level === "ok" && !fs.existsSync(check.message)) {
          throw new Error("AI DevKit reports a missing " + phase + " document as present");
        }
        return check.message;
      });
      process.stdout.write(paths.join("\t"));
    ' 2>/dev/null
)"; then
  IFS=$'\t' read -r REQ DES PLN IMP TST DEP MON <<< "$DOC_PATHS"
else
  echo "Error: AI DevKit lint failed or returned invalid JSON (exit code $LINT_STATUS)."
  printf '%s\n' "$LINT_OUTPUT"
  if [[ -s "$LINT_STDERR_FILE" ]]; then
    cat "$LINT_STDERR_FILE"
  fi
  if [[ "$LINT_STATUS" -eq 0 ]]; then
    exit 1
  fi
  exit "$LINT_STATUS"
fi

echo "=== Status: $FEATURE ==="

# Check which docs exist
for doc in "$REQ" "$DES" "$PLN" "$IMP" "$TST" "$DEP" "$MON"; do
  if exists "$doc"; then
    echo "[EXISTS] $doc"
  else
    echo "[MISS]   $doc"
  fi
done

TOTAL=0
DONE=0
TODO=0
if exists "$PLN"; then
  TOTAL="$(grep -Ec '^[[:space:]]*- \[[ xX]\][[:space:]]+' "$PLN" 2>/dev/null || true)"
  DONE="$(grep -Ec '^[[:space:]]*- \[[xX]\][[:space:]]+' "$PLN" 2>/dev/null || true)"
  if [[ -z "$TOTAL" ]]; then TOTAL=0; fi
  if [[ -z "$DONE" ]]; then DONE=0; fi
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
elif [[ $TOTAL -eq 0 ]]; then
  echo "Phase 4 (Create Initial Plan) — no planning tasks recorded"
elif [[ $TODO -gt 0 ]]; then
  echo "Phase 5 (Execute Plan) — $TODO tasks remaining"
elif ! phase_complete 7; then
  echo "Phase 7 (Check Implementation) — all tasks done, verify against design"
elif ! phase_complete 8; then
  echo "Phase 8 (Write Tests) — implementation check is complete"
elif ! phase_complete 9; then
  echo "Phase 9 (Code Review) — testing is complete"
elif ! exists "$DEP"; then
  echo "No phase suggested: required deployment document is missing: $DEP"
  exit 1
elif ! exists "$MON"; then
  echo "No phase suggested: required monitoring document is missing: $MON"
  exit 1
else
  echo "Lifecycle complete — phases 7, 8, and 9 are recorded as complete"
fi
