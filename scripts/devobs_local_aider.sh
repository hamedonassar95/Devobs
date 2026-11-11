#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'BLOCKED: %s\n' "$1" >&2
  exit 2
}

command -v git >/dev/null 2>&1 || fail "git is required"
command -v docker >/dev/null 2>&1 || fail "Docker with Compose is required"
command -v aider >/dev/null 2>&1 || fail "Aider is missing; see docs/LOCAL_AI_CODE_ASSISTANT.md"
command -v python3 >/dev/null 2>&1 || fail "python3 is required for the local endpoint check"
aider_version="$(aider --no-check-update --no-analytics --version 2>/dev/null)" \
  || fail "could not read the Aider version"
[[ "$aider_version" == *"0.86.2"* ]] \
  || fail "install the documented Aider version 0.86.2"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" \
  || fail "run this from inside a Devobs Git checkout"
case "$(pwd -P)/" in
  "${repo_root%/}/"* ) ;;
  * ) fail "run this from a directory inside the Devobs checkout" ;;
esac

model="${DEVOBS_LOCAL_CODE_MODEL:-}"
[[ -n "$model" ]] || fail "set DEVOBS_LOCAL_CODE_MODEL to a model already installed in Ollama"
[[ ${#model} -le 200 ]] || fail "DEVOBS_LOCAL_CODE_MODEL is too long"
[[ "$model" =~ ^[A-Za-z0-9][A-Za-z0-9._:/-]*$ ]] \
  || fail "DEVOBS_LOCAL_CODE_MODEL has an unsupported name"
case "$model" in
  *[cC][lL][oO][uU][dD]* ) fail "cloud model names are disabled; choose a locally installed model" ;;
esac

if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  fail "the checkout has uncommitted changes; use a clean worktree so the assistant cannot disturb them"
fi

compose_file="$repo_root/models/docker-compose.yml"
compose=(docker compose -f "$compose_file")
"${compose[@]}" exec -T ollama sh -c 'test "${OLLAMA_NO_CLOUD:-}" = "1"' \
  >/dev/null 2>&1 \
  || fail "the Devobs Ollama container is not running with cloud models disabled; follow docs/LOCAL_AI_CODE_ASSISTANT.md"

python3 - "$model" <<'PY'
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


selected = sys.argv[1]
try:
    with build_opener(ProxyHandler({}), RejectRedirects).open(
        "http://127.0.0.1:11434/api/tags", timeout=3,
    ) as response:
        raw = response.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("oversized local model catalog")
    payload = json.loads(raw)
except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
    print(f"BLOCKED: local Ollama endpoint check failed ({type(exc).__name__})", file=sys.stderr)
    sys.exit(2)

models = payload.get("models") if isinstance(payload, dict) else None
names = {
    item.get("name") for item in models
    if isinstance(item, dict) and isinstance(item.get("name"), str)
} if isinstance(models, list) else set()
if selected not in names:
    print("BLOCKED: selected model is not present in local Ollama; install it first", file=sys.stderr)
    sys.exit(2)
PY

export OLLAMA_API_BASE="http://127.0.0.1:11434"
export OLLAMA_NO_CLOUD=1
export NO_PROXY="127.0.0.1,localhost"
export no_proxy="$NO_PROXY"
exec env \
  -u OLLAMA_API_KEY \
  -u OPENAI_API_KEY \
  -u ANTHROPIC_API_KEY \
  -u GEMINI_API_KEY \
  -u GOOGLE_API_KEY \
  -u HTTP_PROXY \
  -u HTTPS_PROXY \
  -u ALL_PROXY \
  -u http_proxy \
  -u https_proxy \
  -u all_proxy \
  aider \
  --config "$repo_root/.aider.conf.yml" \
  --aiderignore "$repo_root/.aiderignore" \
  --model "ollama_chat/$model" \
  --no-auto-commits \
  --no-dirty-commits \
  --no-analytics \
  --no-check-update \
  --subtree-only
