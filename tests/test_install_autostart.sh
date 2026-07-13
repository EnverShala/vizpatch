#!/usr/bin/env bash
set -e

echo "==> Test 1: Syntax-Check (bash -n)"
bash -n scripts/install-autostart.sh
echo "PASS: Syntax valide"

echo "==> Test 2: getent group docker (dynamische GID-Detection)"
grep -q "getent group docker" scripts/install-autostart.sh
echo "PASS: getent group docker drin"

echo "==> Test 3: EnvironmentFile (Pitfall 6)"
grep -q "EnvironmentFile=" scripts/install-autostart.sh
echo "PASS: EnvironmentFile drin"

echo "==> Test 4: Type=oneshot"
grep -q "Type=oneshot" scripts/install-autostart.sh
echo "PASS: Type=oneshot drin"

echo "==> Test 5: systemctl enable vizpatch.service"
grep -q "systemctl enable vizpatch.service" scripts/install-autostart.sh
echo "PASS: systemctl enable drin"

echo "==> Test 6: systemctl disable vizpatch.service"
grep -q "systemctl disable vizpatch.service" scripts/install-autostart.sh
echo "PASS: systemctl disable drin"

echo "==> Test 7: Root-Check via EUID"
grep -q "EUID" scripts/install-autostart.sh
echo "PASS: Root-Check (EUID) drin"

echo "==> Test 8: Non-root-Ausführung gibt sudo-Fehler"
output=$(bash scripts/install-autostart.sh enable 2>&1 || true)
echo "$output" | grep -qiE "sudo|root|EUID|Muss"
echo "PASS: Non-root-Fehlermeldung enthält 'sudo', 'root', 'EUID' oder 'Muss'"

echo "==> Test 9: sed-Idempotenz für DOCKER_GID"
TMP_ENV=$(mktemp)
TMP_BAK="${TMP_ENV}.bak"
trap "rm -f $TMP_ENV $TMP_BAK" EXIT
printf 'IMAP_USER=test@x.de\nDOCKER_GID=999\nWEBUI_USER=admin\n' > "$TMP_ENV"
# Erstes sed (999 -> 999, idempotent)
sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=999|" "$TMP_ENV"
COUNT=$(grep -c "^DOCKER_GID=" "$TMP_ENV")
[[ "$COUNT" == "1" ]] || { echo "FAIL: Erwartet 1 DOCKER_GID-Zeile nach erstem sed, got $COUNT"; exit 1; }
# Zweites sed (999 -> 998)
sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=998|" "$TMP_ENV"
COUNT=$(grep -c "^DOCKER_GID=" "$TMP_ENV")
[[ "$COUNT" == "1" ]] || { echo "FAIL: Erwartet 1 DOCKER_GID-Zeile nach zweitem sed, got $COUNT"; exit 1; }
grep -q "^DOCKER_GID=998$" "$TMP_ENV" || { echo "FAIL: DOCKER_GID sollte 998 sein"; exit 1; }
echo "PASS: sed-Idempotenz OK (999 -> 998, nur eine Zeile)"

echo ""
echo "All install-autostart.sh checks passed"
