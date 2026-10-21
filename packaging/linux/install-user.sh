#!/bin/sh
set -eu

PREFIX="${PREFIX:-$HOME/.local}"
AUTOSTART=0

usage() {
    cat <<'EOF'
Uso: install-user.sh [--autostart] [--prefix DIR]

Instala o Learning Helper apenas para o usuário atual, sem root.
  --autostart   inicia junto com a sessão (opcional)
  --prefix DIR  prefixo de instalação (padrão: ~/.local)
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --autostart) AUTOSTART=1 ;;
        --prefix)
            shift
            if [ "$#" -eq 0 ]; then
                echo "Faltou o diretório do --prefix." >&2
                exit 1
            fi
            PREFIX="$1"
            ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Opção desconhecida: $1" >&2
            usage
            exit 1
            ;;
    esac
    shift
done

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BINARY="$HERE/learning-helper"
if [ ! -x "$BINARY" ] || [ ! -d "$HERE/_internal" ]; then
    echo "Pacote incompleto: esperava $BINARY e $HERE/_internal." >&2
    exit 1
fi
if [ ! -f "$HERE/learning-helper.png" ]; then
    echo "Pacote incompleto: falta $HERE/learning-helper.png." >&2
    exit 1
fi
if [ ! -f "$HERE/uninstall-user.sh" ]; then
    echo "Pacote incompleto: falta $HERE/uninstall-user.sh." >&2
    exit 1
fi

TARGET="$PREFIX/opt/learning-helper"
BIN_DIR="$PREFIX/bin"
ICON_DIR="$PREFIX/share/icons/hicolor/256x256/apps"
APPS_DIR="$PREFIX/share/applications"

echo "Instalando em $TARGET"
rm -rf "$TARGET"
mkdir -p "$TARGET"
cp -a "$BINARY" "$HERE/_internal" "$TARGET/"

mkdir -p "$BIN_DIR"
rm -f "$BIN_DIR/learning-helper"
ln -s "$TARGET/learning-helper" "$BIN_DIR/learning-helper"

install -m 755 "$HERE/uninstall-user.sh" "$BIN_DIR/learning-helper-uninstall"

mkdir -p "$ICON_DIR"
install -m 644 "$HERE/learning-helper.png" "$ICON_DIR/learning-helper.png"

mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/learning-helper.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Learning Helper
Comment=Desafios curtos para aprender
Exec="$TARGET/learning-helper"
Icon=learning-helper
Terminal=false
Categories=Education;
Actions=Settings;Statistics;

[Desktop Action Settings]
Name=Configurações
Exec="$TARGET/learning-helper" --settings

[Desktop Action Statistics]
Name=Estatísticas
Exec="$TARGET/learning-helper" --stats
EOF

cat > "$APPS_DIR/learning-helper-settings.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Learning Helper — Configurações
Comment=Ajustar desafios, módulos e rotina
Exec="$TARGET/learning-helper" --settings
Icon=learning-helper
Terminal=false
Categories=Education;Settings;
EOF

cat > "$APPS_DIR/learning-helper-stats.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Learning Helper — Estatísticas
Comment=Ver tentativas, acertos e níveis
Exec="$TARGET/learning-helper" --stats
Icon=learning-helper
Terminal=false
Categories=Education;Utility;
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

if [ "$AUTOSTART" = "1" ]; then
    "$BIN_DIR/learning-helper" --enable-autostart
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "Dica: adicione $BIN_DIR ao PATH para usar o comando 'learning-helper'." ;;
esac

echo "Pronto. Para desinstalar: $BIN_DIR/learning-helper-uninstall"
