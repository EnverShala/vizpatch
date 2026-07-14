#!/usr/bin/env bash
# scripts/build-deployment-package.sh
# Erzeugt ein Deployment-Paket v1.1.0 für USB-Delivery zum Kunden (Agent + WebUI).
# Voraussetzung: Docker + Docker Compose Plugin auf dem Build-Host (Vizionists-Laptop).
#
# Aufruf: bash scripts/build-deployment-package.sh [VERSION]
#   VERSION default: v1.1.0 (Semver-Tag)
#
# Ergebnis: dist/deployment-paket-<VERSION>/
#   vizpatch-<VERSION>.tar                 Agent-Image-Tarball
#   vizpatch-<VERSION>.tar.sha256          SHA256-Checksum Agent
#   vizpatch-webui-<VERSION>.tar           WebUI-Image-Tarball
#   vizpatch-webui-<VERSION>.tar.sha256    SHA256-Checksum WebUI
#   docker-compose.yml                     Compose-Datei für den Kundenserver (beide Services)
#   README.md                              Setup-Anleitung (Phase 4)
#   prompts/                               classify.txt + generate.txt + context-seed.txt
#   deployment/                            Konfigurationsvorlagen
#   scripts/                               install-autostart.sh
#
# USB-Transfer: den gesamten dist/deployment-paket-<VERSION>/-Ordner auf USB kopieren.

set -euo pipefail

VERSION="${1:-v1.1.0}"
AGENT_IMAGE_TAG="vizpatch:${VERSION}"
WEBUI_IMAGE_TAG="vizpatch-webui:${VERSION}"
DIST_DIR="dist/deployment-paket-${VERSION}"
AGENT_TAR="vizpatch-${VERSION}.tar"
WEBUI_TAR="vizpatch-webui-${VERSION}.tar"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Build Agent-Image ${AGENT_IMAGE_TAG}"
docker build -t "${AGENT_IMAGE_TAG}" agent/

echo "==> Build WebUI-Image ${WEBUI_IMAGE_TAG}"
docker build -t "${WEBUI_IMAGE_TAG}" webui/

echo "==> Zielordner anlegen: ${DIST_DIR}"
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}/deployment"
mkdir -p "${DIST_DIR}/prompts"
mkdir -p "${DIST_DIR}/scripts"
mkdir -p "${DIST_DIR}/config"
# Marker damit tar/cp den leeren Ordner mitnimmt — WebUI-Entrypoint füllt ihn beim ersten Start
touch "${DIST_DIR}/config/.gitkeep"

echo "==> docker save Agent -> Tarball"
docker save "${AGENT_IMAGE_TAG}" -o "${DIST_DIR}/${AGENT_TAR}"

echo "==> docker save WebUI -> Tarball"
docker save "${WEBUI_IMAGE_TAG}" -o "${DIST_DIR}/${WEBUI_TAR}"

echo "==> docker-compose.yml kopieren (Phase-4-Compose mit beiden Services)"
cp deployment/docker-compose.phase4.yml "${DIST_DIR}/docker-compose.yml"

echo "==> Prompts kopieren (Agent-Prompts + WebUI context-seed.txt)"
cp agent/prompts/*.txt "${DIST_DIR}/prompts/"
cp webui/prompts/context-seed.txt "${DIST_DIR}/prompts/"

echo "==> Deployment-Templates kopieren"
cp deployment/kunde-env.example                       "${DIST_DIR}/deployment/kunde-env.example"
cp deployment/vizionists-test-env.example             "${DIST_DIR}/deployment/vizionists-test-env.example"
cp deployment/context.md.tankstelle-erstversion.md    "${DIST_DIR}/deployment/context.md.tankstelle-erstversion.md"
cp deployment/context.md.vizionists-test.md           "${DIST_DIR}/deployment/context.md.vizionists-test.md"

echo "==> install-autostart.sh kopieren"
cp scripts/install-autostart.sh "${DIST_DIR}/scripts/install-autostart.sh"
chmod +x "${DIST_DIR}/scripts/install-autostart.sh"

echo "==> README kopieren (Phase-4-Setup-Anleitung)"
cp deployment/README.phase4.md "${DIST_DIR}/README.md"

echo "==> SHA256-Checksums berechnen"
( cd "${DIST_DIR}" && sha256sum "${AGENT_TAR}" > "${AGENT_TAR}.sha256" )
( cd "${DIST_DIR}" && sha256sum "${WEBUI_TAR}" > "${WEBUI_TAR}.sha256" )

echo ""
echo "==> Fertig. Inhalt:"
ls -la "${DIST_DIR}"
echo ""
echo "USB-Transfer: den gesamten Ordner ${DIST_DIR} auf USB kopieren."
echo "Auf Kundenserver:"
echo "  sha256sum -c ${AGENT_TAR}.sha256"
echo "  sha256sum -c ${WEBUI_TAR}.sha256"
echo "  docker load -i ${AGENT_TAR}"
echo "  docker load -i ${WEBUI_TAR}"
echo "  export DOCKER_GID=\$(stat -c '%g' /var/run/docker.sock)"
echo "  docker compose up -d webui"
echo "  Browser: http://<server-ip>:8080/ — Zero-Config-Setup"
