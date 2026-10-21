#!/bin/sh
set -eu

PREFIX="${PREFIX:-$HOME/.local}"
PURGE=0
SELF=$0
case "$SELF" in
    /*) ;;
    *) SELF="$PWD/$SELF" ;;
esac

usage() {
    cat <<'EOF'
Uso: uninstall-user.sh [--purge]

Remove o Learning Helper instalado pelo install-user.sh no usuário atual.
  --purge   remove também o banco de dados e os logs (~/.local/share/learning_helper)
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --purge) PURGE=1 ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Opção desconhecida: $1" >&2
            usage
            exit 1
            ;;
    esac
    shift
done

TARGET="$PREFIX/opt/learning-helper"
BIN_DIR="$PREFIX/bin"
APPS_DIR="$PREFIX/share/applications"
ICON_DIR="$PREFIX/share/icons/hicolor/256x256/apps"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

rm -rf "$TARGET"
rm -f "$BIN_DIR/learning-helper"
rm -f "$APPS_DIR/learning-helper.desktop"
rm -f "$APPS_DIR/learning-helper-settings.desktop"
rm -f "$APPS_DIR/learning-helper-stats.desktop"
rm -f "$ICON_DIR/learning-helper.png"
rm -f "$CONFIG_HOME/autostart/learning-helper.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

if [ "$PURGE" = "1" ]; then
    rm -rf "$DATA_HOME/learning_helper"
    echo "Dados removidos de $DATA_HOME/learning_helper"
else
    echo "Banco e logs preservados em $DATA_HOME/learning_helper (use --purge para remover)."
fi

if [ "$SELF" = "$BIN_DIR/learning-helper-uninstall" ]; then
    rm -f "$SELF"
fi

echo "Learning Helper removido de $PREFIX."
