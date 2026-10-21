#!/bin/sh
set -eu

ARCHIVE="${1:?informe o caminho do tar.gz por usuário}"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/home" "$WORK/extract"
tar -xzf "$ARCHIVE" -C "$WORK/extract"
PACKAGE=$(find "$WORK/extract" -maxdepth 1 -type d -name "LearningHelper-*" | head -n 1)
if [ -z "$PACKAGE" ]; then
    echo "Pacote não encontrado dentro de $ARCHIVE" >&2
    exit 1
fi

HOME="$WORK/home" "$PACKAGE/install-user.sh" --autostart
HOME="$WORK/home" "$WORK/home/.local/bin/learning-helper" --self-check
test -f "$WORK/home/.config/autostart/learning-helper.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
grep -q -- "--settings" "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
grep -q -- "--stats" "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
test -x "$WORK/home/.local/opt/learning-helper/learning-helper"

HOME="$WORK/home" "$WORK/home/.local/bin/learning-helper-uninstall"
test ! -e "$WORK/home/.local/opt/learning-helper"
test ! -e "$WORK/home/.config/autostart/learning-helper.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
echo "install/uninstall por usuário: ok"
