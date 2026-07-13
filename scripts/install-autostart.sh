#!/usr/bin/env bash
# install-autostart.sh — installiert oder entfernt vizpatch.service
# Muss mit sudo laufen. Idempotent.
#
# Aufruf:
#   sudo ./install-autostart.sh enable    # systemd-Unit installieren + enable
#   sudo ./install-autostart.sh disable   # systemd-Unit disable + entfernen
#   sudo ./install-autostart.sh status    # Aktueller Zustand

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Muss mit sudo/root laufen. Neu: sudo $0 ${*}"
  exit 1
fi

ACTION="${1:-status}"
UNIT_PATH="/etc/systemd/system/vizpatch.service"
DEPLOY_DIR="${VIZPATCH_DIR:-/opt/vizpatch}"

case "$ACTION" in
  enable)
    if [[ ! -d "$DEPLOY_DIR" ]]; then
      echo "ERROR: $DEPLOY_DIR existiert nicht. Erst docker compose up -d im Deployment-Ordner."
      exit 1
    fi
    if ! command -v docker >/dev/null 2>&1; then
      echo "ERROR: docker nicht gefunden."
      exit 1
    fi
    DOCKER_GID=$(getent group docker | cut -d: -f3)
    if [[ -z "$DOCKER_GID" ]]; then
      echo "WARNING: docker-Gruppe nicht gefunden. DOCKER_GID leer."
    fi
    # Idempotentes sed-Replace für DOCKER_GID (W6-Fix)
    if grep -q '^DOCKER_GID=' "$DEPLOY_DIR/.env" 2>/dev/null; then
      sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=$DOCKER_GID|" "$DEPLOY_DIR/.env"
    else
      echo "DOCKER_GID=$DOCKER_GID" >> "$DEPLOY_DIR/.env"
    fi
    # AUTOSTART_ENABLED=true setzen
    if grep -q '^AUTOSTART_ENABLED=' "$DEPLOY_DIR/.env" 2>/dev/null; then
      sed -i.bak "s|^AUTOSTART_ENABLED=.*|AUTOSTART_ENABLED=true|" "$DEPLOY_DIR/.env"
    else
      echo "AUTOSTART_ENABLED=true" >> "$DEPLOY_DIR/.env"
    fi
    DOCKER_BIN="$(which docker)"
    cat > "$UNIT_PATH" <<EOF
[Unit]
Description=Vizpatch — KI-Email-Agent Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$DOCKER_BIN compose up -d
ExecStop=$DOCKER_BIN compose down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable vizpatch.service
    echo "OK: vizpatch.service installiert und aktiviert."
    echo "Hinweis: sudo reboot zum Testen des Autostart."
    ;;
  disable)
    if [[ -f "$UNIT_PATH" ]]; then
      systemctl disable vizpatch.service || true
      rm -f "$UNIT_PATH"
      systemctl daemon-reload
    fi
    if grep -q '^AUTOSTART_ENABLED=' "$DEPLOY_DIR/.env" 2>/dev/null; then
      sed -i.bak "s|^AUTOSTART_ENABLED=.*|AUTOSTART_ENABLED=false|" "$DEPLOY_DIR/.env"
    fi
    echo "OK: vizpatch.service deaktiviert und entfernt."
    ;;
  status)
    if [[ -f "$UNIT_PATH" ]]; then
      systemctl status vizpatch.service --no-pager || true
    else
      echo "vizpatch.service ist NICHT installiert."
    fi
    ;;
  *)
    echo "Usage: sudo $0 enable|disable|status"
    exit 1
    ;;
esac
