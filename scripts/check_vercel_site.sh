#!/usr/bin/env bash
set -euo pipefail

SITE_URL="${SITE_URL:-}"
EXPECTED_SHA="${EXPECTED_SHA:-}"
CONTRACT_FILE="${CONTRACT_FILE:-site-contract.json}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-12}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-10}"
VERCEL_AUTOMATION_BYPASS_SECRET="${VERCEL_AUTOMATION_BYPASS_SECRET:-}"

if [[ -z "$SITE_URL" ]]; then
  echo "::error::Set SITE_URL to the preview deployment URL."
  exit 2
fi
if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "::error::EXPECTED_SHA must be a full lowercase commit SHA."
  exit 2
fi
if [[ ! "$MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ || ! "$POLL_INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || (( MAX_ATTEMPTS > 12 )); then
  echo "::error::Polling settings must use 1 to 12 attempts and a non-negative integer delay."
  exit 2
fi
if [[ ! -f "$CONTRACT_FILE" ]]; then
  echo "::error::Site contract not found: $CONTRACT_FILE"
  exit 2
fi
for tool in curl jq python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "::error::Required health-check tool is missing: $tool"
    exit 2
  fi
done
if ! jq -e '
  .required_text_any
  | type == "array" and length > 0 and all(.[]; type == "string" and length > 0)
' "$CONTRACT_FILE" >/dev/null 2>&1; then
  echo "::error::Site contract must be valid JSON with a non-empty required_text_any list of non-empty strings."
  exit 2
fi
WORK_DIR="$(mktemp -d)"
cleanup() {
  rm -f -- "$WORK_DIR/bypass.curlrc" "$WORK_DIR/curl.err" \
    "$WORK_DIR/site.html" "$WORK_DIR/deployment.json" "$WORK_DIR/private.html"
  rmdir "$WORK_DIR" 2>/dev/null || true
}
trap cleanup EXIT
CURL_CONFIG_ARGS=()
if [[ -n "$VERCEL_AUTOMATION_BYPASS_SECRET" ]]; then
  (umask 077; printf 'header = "x-vercel-protection-bypass: %s"\n' "$VERCEL_AUTOMATION_BYPASS_SECRET" > "$WORK_DIR/bypass.curlrc")
  CURL_CONFIG_ARGS=(--config "$WORK_DIR/bypass.curlrc")
fi

python3 - "$SITE_URL" "${ALLOW_INSECURE_LOCALHOST:-false}" <<'PY'
import sys
from urllib.parse import urlsplit

url = urlsplit(sys.argv[1])
allow_local_http = sys.argv[2] == "true"
if url.username or url.password or url.query or url.fragment:
    raise SystemExit("SITE_URL must not contain credentials, query, or fragment")
if url.scheme == "https" and url.hostname:
    raise SystemExit(0)
if allow_local_http and url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit(0)
raise SystemExit("SITE_URL must use HTTPS (HTTP is allowed only for explicit loopback tests)")
PY

SITE_ROOT="${SITE_URL%/}"
SITE_ROOT="${SITE_ROOT%/}"
SITE_ROOT_PATH="$(python3 - "$SITE_ROOT" <<'PY'
import sys
from urllib.parse import urlsplit
print(urlsplit(sys.argv[1]).path.rstrip("/"))
PY
)"
BASE_URL="${SITE_ROOT%$SITE_ROOT_PATH}"
if [[ -z "$BASE_URL" ]]; then BASE_URL="$SITE_ROOT"; fi
if [[ -n "$SITE_ROOT_PATH" ]]; then SITE_ROOT="$BASE_URL$SITE_ROOT_PATH"; fi

required_texts="$(jq -r '.required_text_any[]' "$CONTRACT_FILE")"
accepted_texts="$(jq -c '.required_text_any' "$CONTRACT_FILE")"

http_status=""
http_effective_url=""
http_redirects=""
http_content_type=""
http_get() {
  local url="$1" output="$2" max_time="$3" result curl_status
  local -a args=(--max-redirs 0 --silent --show-error --connect-timeout 5 \
    --max-time "$max_time" --output "$output" --write-out $'%{http_code}\\t%{url_effective}\\t%{num_redirects}\\t%{content_type}')
  if [[ -n "$VERCEL_AUTOMATION_BYPASS_SECRET" ]]; then
    # Never forward the bypass credential to a redirect destination.
    :
  else
    args+=(--location --max-redirs 5)
  fi
  if result="$(curl "${args[@]}" "${CURL_CONFIG_ARGS[@]}" "$url" 2>"$WORK_DIR/curl.err")"; then
    IFS=$'\t' read -r http_status http_effective_url http_redirects http_content_type <<< "$result"
    return 0
  else
    curl_status=$?
    echo "::error::HTTP request failed (curl exit $curl_status) for $url: $(cat "$WORK_DIR/curl.err")"
    return 1
  fi
}

is_auth_or_protection_response() {
  local body="$1" effective_url="$2"
  if python3 - "$effective_url" <<'PY'
import sys
from urllib.parse import urlsplit

path = urlsplit(sys.argv[1]).path.lower()
segments = {part for part in path.split("/") if part}
raise SystemExit(0 if segments.intersection({"login", "signin", "sign-in", "auth", "authentication", "sso"}) else 1)
PY
  then
    return 0
  fi
  grep -Eiq '(<title[^>]*>[^<]*(sign[[:space:]-]*in|log[[:space:]-]*in|authentication|deployment protection|verify you are human)|authentication required|deployment is protected|sign in to continue|please sign in|login required|protected by vercel|vercel authentication|verify your identity)' "$body"
}

if ! http_get "$SITE_ROOT/" "$WORK_DIR/site.html" 15; then
  exit 1
fi
page_status="$http_status"
if [[ "$page_status" != "200" ]]; then
  echo "::error::Site root returned HTTP $page_status, expected 200. If Vercel Deployment Protection blocked the request, add VERCEL_AUTOMATION_BYPASS_SECRET to the GitHub Actions environment secrets; the check will not skip."
  exit 1
fi
if is_auth_or_protection_response "$WORK_DIR/site.html" "$http_effective_url"; then
  echo "::error::Site root returned a login or Deployment Protection response. If protection is enabled, store VERCEL_AUTOMATION_BYPASS_SECRET as a GitHub Actions environment secret for vercel-staging."
  exit 1
fi
if [[ ! -s "$WORK_DIR/site.html" || "$http_content_type" != text/html* && "$http_content_type" != application/xhtml+xml* ]]; then
  echo "::error::Site root returned an empty body or non-HTML content type ($http_content_type)."
  exit 1
fi
brand_matched=false
while IFS= read -r required_text; do
  if grep -Fq -- "$required_text" "$WORK_DIR/site.html"; then
    brand_matched=true
    break
  fi
done <<< "$required_texts"
if [[ "$brand_matched" != "true" ]]; then
  echo "::error::The deployed page contains none of the accepted brand text: $accepted_texts"
  exit 1
fi

manifest_status=""
deployed_sha=""
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if ! http_get "$SITE_ROOT/deployment.json?run_id=${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}-${attempt}" "$WORK_DIR/deployment.json" 10; then
    exit 1
  fi
  manifest_status="$http_status"
  if [[ "$manifest_status" == "200" ]]; then
    if is_auth_or_protection_response "$WORK_DIR/deployment.json" "$http_effective_url"; then
      echo "::error::Deployment manifest request returned a login or Deployment Protection response. Configure VERCEL_AUTOMATION_BYPASS_SECRET as an environment secret if protection is enabled."
      exit 1
    fi
    deployed_sha="$(jq -er 'select(.schema_version == 1) | .source_sha | select(test("^[0-9a-f]{40}$"))' "$WORK_DIR/deployment.json" 2>/dev/null || true)"
    if [[ "$deployed_sha" == "$EXPECTED_SHA" ]]; then
      break
    fi
  fi
  if (( attempt < MAX_ATTEMPTS )); then sleep "$POLL_INTERVAL_SECONDS"; fi
done
if [[ "$manifest_status" != "200" || "$deployed_sha" != "$EXPECTED_SHA" ]]; then
  echo "::error::Deployment manifest did not report expected SHA $EXPECTED_SHA after $MAX_ATTEMPTS attempts (HTTP $manifest_status, SHA ${deployed_sha:-missing})."
  exit 1
fi

for private_path in \
  /scripts/check_site.py \
  /docs/CI.md \
  /README.md \
  /site-contract.json; do
  if ! http_get "$SITE_ROOT$private_path?health_check=${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}" "$WORK_DIR/private.html" 10; then
    exit 1
  fi
  if is_auth_or_protection_response "$WORK_DIR/private.html" "$http_effective_url"; then
    echo "::error::Private repository path $private_path resolved to a login or Deployment Protection response; it must return a direct HTTP 404."
    exit 1
  fi
  if [[ "$http_status" != "404" || "$http_redirects" != "0" ]]; then
    echo "::error::Private repository path $private_path ended at HTTP $http_status after $http_redirects redirects; expected a direct HTTP 404."
    exit 1
  fi
done

echo "Vercel site health check passed for source commit $EXPECTED_SHA." >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
echo "Vercel site health check passed for source commit $EXPECTED_SHA."
