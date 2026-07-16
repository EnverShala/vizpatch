#!/bin/sh
set -e

# Zero-Config-Bootstrap: sorge dafür dass /config/.env und /config/context.md existieren,
# damit WebUI sofort startbar ist. WebUI läuft danach mit Default-Login admin/admin
# und zeigt einen Warn-Banner bis der Kunde eigene Credentials speichert.

CONFIG_DIR="${WEBUI_CONFIG_DIR:-/config}"

mkdir -p "$CONFIG_DIR"

if [ ! -e "$CONFIG_DIR/.env" ]; then
  touch "$CONFIG_DIR/.env"
  chmod 600 "$CONFIG_DIR/.env" 2>/dev/null || true
fi

if [ ! -e "$CONFIG_DIR/context.md" ]; then
  touch "$CONFIG_DIR/context.md"
fi

# Multi-Agent-Migration (MA-01, D-47): bestehendes Single-Agent-Layout wird idempotent
# nach agents/default ueberfuehrt, bevor die erste Route bedient wird. No-Op bei
# frischer/leerer Config (Guard in migration.py verhindert Phantom-Agenten, D-50).
python3 -c "from src.migration import migrate; migrate()"

exec "$@"
