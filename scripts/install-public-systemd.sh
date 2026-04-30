#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
USER_NAME="$(stat -c '%U' "$ROOT")"
GROUP_NAME="$(stat -c '%G' "$ROOT")"

render_unit() {
  local template="$1"
  local target="$2"

  sed \
    -e "s|__ROOT__|$ROOT|g" \
    -e "s|__USER__|$USER_NAME|g" \
    -e "s|__GROUP__|$GROUP_NAME|g" \
    "$template" >"$target"
}

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo ./scripts/install-public-systemd.sh" >&2
  exit 1
fi

render_unit \
  "$ROOT/ops/systemd/tech-card-public-backend.service.template" \
  "$SYSTEMD_DIR/tech-card-public-backend.service"
render_unit \
  "$ROOT/ops/systemd/tech-card-public-frontend.service.template" \
  "$SYSTEMD_DIR/tech-card-public-frontend.service"

systemctl daemon-reload
systemctl enable --now tech-card-public-backend.service
systemctl enable --now tech-card-public-frontend.service
systemctl restart tech-card-public-backend.service
systemctl restart tech-card-public-frontend.service
