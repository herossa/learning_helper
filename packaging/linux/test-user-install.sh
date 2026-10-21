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

HOME="$WORK/home" "$WORK/home/.local/bin/learning-helper" \
    --stats-server --stats-port 8599 > "$WORK/stats.log" 2>&1 &
STATS_PID=$!
cleanup() {
    kill "$STATS_PID" 2>/dev/null || true
}
trap 'cleanup; rm -rf "$WORK"' EXIT
sleep 2
if ! kill -0 "$STATS_PID" 2>/dev/null; then
    echo "servidor de estatísticas não iniciou" >&2
    cat "$WORK/stats.log"
    exit 1
fi

test -f "$WORK/home/.config/autostart/learning-helper.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
test -f "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
grep -q -- "--settings" "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
grep -q -- "--stats" "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
test -x "$WORK/home/.local/opt/learning-helper/learning-helper"

HOME="$WORK/home" "$WORK/home/.local/bin/learning-helper-uninstall"
process_pattern="($WORK/home/.local/bin/learning-helper|$WORK/home/.local/opt/learning-helper/learning-helper)( |\$)"
i=0
while [ "$i" -lt 20 ] && pgrep -f -- "$process_pattern" >/dev/null 2>&1; do
    sleep 0.5
    i=$((i + 1))
done
if pgrep -f -- "$process_pattern" >/dev/null 2>&1; then
    echo "desinstalador não encerrou o processo em execução" >&2
    cat "$WORK/stats.log"
    exit 1
fi
test ! -e "$WORK/home/.local/opt/learning-helper"
test ! -e "$WORK/home/.config/autostart/learning-helper.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper-settings.desktop"
test ! -e "$WORK/home/.local/share/applications/learning-helper-stats.desktop"
echo "install/uninstall por usuário: ok"
