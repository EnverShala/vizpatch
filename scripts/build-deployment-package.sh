#!/usr/bin/env bash
# scripts/build-deployment-package.sh
# Erzeugt ein Deployment-Paket für USB-Delivery zum Kunden.
# Voraussetzung: Docker + Docker Compose Plugin auf dem Build-Host (Vizionists-Laptop).
#
# Aufruf: bash scripts/build-deployment-package.sh [VERSION]
#   VERSION default: v1.0.0 (Semver-Tag)
#
# Ergebnis: dist/deployment-paket-<VERSION>/
#   vizpatch-<VERSION>.tar        Docker-Image-Tarball
#   vizpatch-<VERSION>.tar.sha256 SHA256-Checksum (Integritätsprüfung vor docker load)
#   docker-compose.yml                  Compose-Datei für den Kundenserver
#   README.md                           Setup-Anleitung
#   prompts/                            classify.txt + generate.txt (Bind-Mount-Quelle)
#   deployment/                         Konfigurationsvorlagen
#     kunde-env.example                 Kunden-Template (Pflichtfelder mit Platzhaltern)
#     vizionists-test-env.example       Vizionists-Test-Config (IONOS, shala@vizionists.com)
#     context.md.tankstelle-erstversion.md  OSINT-Rohbau für Tankstelle
#     context.md.vizionists-test.md     Vizionists-Test-Kontext
#
# USB-Transfer: den gesamten dist/deployment-paket-<VERSION>/-Ordner auf USB kopieren.
# Auf Kundenserver: docker load -i vizpatch-<VERSION>.tar && docker compose up -d

set -euo pipefail

VERSION="${1:-v1.0.0}"
IMAGE_TAG="vizpatch:${VERSION}"
DIST_DIR="dist/deployment-paket-${VERSION}"
TAR_NAME="vizpatch-${VERSION}.tar"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Build Docker-Image ${IMAGE_TAG}"
docker build -t "${IMAGE_TAG}" agent/

echo "==> Zielordner anlegen: ${DIST_DIR}"
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}/deployment"
mkdir -p "${DIST_DIR}/prompts"

echo "==> docker save -> Tarball"
docker save "${IMAGE_TAG}" -o "${DIST_DIR}/${TAR_NAME}"

echo "==> docker-compose.yml kopieren"
cp agent/docker-compose.yml "${DIST_DIR}/docker-compose.yml"

echo "==> Prompts kopieren (Bind-Mount-Quelle)"
cp agent/prompts/*.txt "${DIST_DIR}/prompts/"

echo "==> Deployment-Templates kopieren"
cp deployment/kunde-env.example                       "${DIST_DIR}/deployment/kunde-env.example"
cp deployment/vizionists-test-env.example             "${DIST_DIR}/deployment/vizionists-test-env.example"
cp deployment/context.md.tankstelle-erstversion.md    "${DIST_DIR}/deployment/context.md.tankstelle-erstversion.md"
cp deployment/context.md.vizionists-test.md           "${DIST_DIR}/deployment/context.md.vizionists-test.md"

echo "==> README kopieren"
cp agent/README.md "${DIST_DIR}/README.md"

echo "==> SHA256-Checksum berechnen"
( cd "${DIST_DIR}" && sha256sum "${TAR_NAME}" > "${TAR_NAME}.sha256" )

echo ""
echo "==> Fertig. Inhalt:"
ls -la "${DIST_DIR}"
echo ""
echo "USB-Transfer: den gesamten Ordner ${DIST_DIR} auf USB kopieren."
echo "Auf Kundenserver:"
echo "  sha256sum -c ${TAR_NAME}.sha256   # Tarball-Integrität prüfen (T-02.04-01)"
echo "  docker load -i ${TAR_NAME}"
echo "  docker compose up -d"
