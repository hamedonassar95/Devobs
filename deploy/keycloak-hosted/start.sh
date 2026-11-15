#!/bin/bash
set -euo pipefail

reject() { printf 'devobs-keycloak: invalid_hosted_configuration\n' >&2; return 1; }

valid_dns() {
  local label
  [[ "$1" != *..* && "$1" == *.* && ${#1} -le 253 ]] || return 1
  local -a labels
  IFS=. read -r -a labels <<< "$1"
  for label in "${labels[@]}"; do
    [[ "$label" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]] || return 1
  done
}

validate_config() {
  local name host port database ca callback
  for name in RENDER_EXTERNAL_URL DEVOBS_OIDC_REDIRECT_URI DEVOBS_KEYCLOAK_DB_HOST \
    DEVOBS_KEYCLOAK_DB_NAME KC_DB_USERNAME KC_DB_PASSWORD \
    KC_BOOTSTRAP_ADMIN_USERNAME KC_BOOTSTRAP_ADMIN_PASSWORD; do
    [[ -n "${!name:-}" ]] || { reject; return 1; }
  done
  [[ "$RENDER_EXTERNAL_URL" =~ ^https://devobs-keycloak-hosted(-[a-z0-9-]+)?\.onrender\.com$ ]] || { reject; return 1; }
  callback="$DEVOBS_OIDC_REDIRECT_URI"
  [[ "$callback" =~ ^https://[a-z0-9][a-z0-9.-]+\.[a-z]{2,}/[a-zA-Z0-9/_-]+$ ]] || { reject; return 1; }
  host="${callback#https://}"; host="${host%%/*}"
  valid_dns "$host" || { reject; return 1; }
  case "$host" in localhost|*.localhost|*.invalid|*.test|*.example|example.com|*.example.com) reject; return 1;; esac
  export DEVOBS_OIDC_CLIENT_ORIGIN="https://$host"

  host="$DEVOBS_KEYCLOAK_DB_HOST"
  # This profile is Frankfurt-only. Render's internal Postgres route cannot
  # verify the peer certificate; require its external DNS name, never an alias.
  # https://render.com/docs/postgresql-creating-connecting
  [[ "$host" =~ ^dpg-[a-z0-9]+(-[a-z0-9]+)*\.frankfurt-postgres\.render\.com$ ]] || { reject; return 1; }
  valid_dns "$host" || { reject; return 1; }
  database="$DEVOBS_KEYCLOAK_DB_NAME"
  [[ "$database" =~ ^[a-z][a-z0-9_]{0,62}$ ]] || { reject; return 1; }
  [[ "$KC_DB_USERNAME" =~ ^[a-z][a-z0-9_]{0,62}$ ]] || { reject; return 1; }
  port="${DEVOBS_KEYCLOAK_DB_PORT:-5432}"
  [[ "$port" =~ ^[0-9]{1,5}$ ]] && (( 10#$port >= 1 && 10#$port <= 65535 )) || { reject; return 1; }
  ca="${DEVOBS_KEYCLOAK_DB_CA_FILE:-/etc/secrets/keycloak-db-ca.pem}"
  # Fixed mount path in deployment; an explicit file path supports isolated tests.
  [[ "$ca" =~ ^/[a-zA-Z0-9_./-]+$ && -f "$ca" && -r "$ca" ]] || { reject; return 1; }
  export KC_DB_URL="jdbc:postgresql://$host:$port/$database?sslmode=verify-full&sslrootcert=$ca"

  port="${PORT:-10000}"
  [[ "$port" =~ ^[0-9]{1,5}$ ]] && (( 10#$port >= 1 && 10#$port <= 65535 )) || { reject; return 1; }
  export KC_HOSTNAME="$RENDER_EXTERNAL_URL" KC_HOSTNAME_STRICT=true
  export KC_HTTP_ENABLED=true KC_HTTP_PORT="$port" KC_PROXY_HEADERS=xforwarded
  export KC_DB_POOL_INITIAL_SIZE=1 KC_DB_POOL_MIN_SIZE=1 KC_DB_POOL_MAX_SIZE=5
}

main() {
  validate_config || return 1
  exec /opt/keycloak/bin/kc.sh start --optimized --import-realm
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
