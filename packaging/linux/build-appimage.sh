#!/bin/sh
set -eu

VERSION="${1:?informe a versão, ex.: 0.2.0}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD="$ROOT/build/appimage"
APPDIR="$BUILD/AppDir"
OUTPUT="$ROOT/dist/LearningHelper-${VERSION}-x86_64.AppImage"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"
APPIMAGETOOL_ARGS="${APPIMAGETOOL_ARGS:-}"

if [ ! -x "$ROOT/dist/learning-helper/learning-helper" ]; then
    echo "Rode o PyInstaller antes: dist/learning-helper/learning-helper não encontrado." >&2
    exit 1
fi

rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$ROOT/dist/learning-helper/." "$APPDIR/usr/bin/"
install -m 644 \
    "$ROOT/packaging/icons/learning-helper.png" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps/learning-helper.png"
install -m 644 \
    "$ROOT/packaging/icons/learning-helper.png" \
    "$APPDIR/learning-helper.png"

cat > "$APPDIR/learning-helper.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Learning Helper
Comment=Desafios curtos para aprender
Exec=learning-helper
Icon=learning-helper
Terminal=false
Categories=Education;
EOF

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$HERE/usr/bin/learning-helper" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# AppImage exige um ícone no diretório raiz e um desktop entry.
ARCH=x86_64
export ARCH
# shellcheck disable=SC2086
"$APPIMAGETOOL" $APPIMAGETOOL_ARGS "$APPDIR" "$OUTPUT"
echo "AppImage gerado em $OUTPUT"
