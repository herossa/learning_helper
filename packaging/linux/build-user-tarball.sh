#!/bin/sh
set -eu

VERSION="${1:?informe a versão, ex.: 0.2.0}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
STAGE_ROOT="$ROOT/build/linux-user"
STAGE="$STAGE_ROOT/LearningHelper-$VERSION"
OUTPUT="$ROOT/dist/LearningHelper-${VERSION}-linux-x86_64.tar.gz"

if [ ! -x "$ROOT/dist/learning-helper/learning-helper" ]; then
    echo "Rode o PyInstaller antes: dist/learning-helper/learning-helper não encontrado." >&2
    exit 1
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -a "$ROOT/dist/learning-helper/." "$STAGE/"
install -m 755 "$ROOT/packaging/linux/install-user.sh" "$STAGE/install-user.sh"
install -m 755 "$ROOT/packaging/linux/uninstall-user.sh" "$STAGE/uninstall-user.sh"
install -m 644 "$ROOT/packaging/icons/learning-helper.png" "$STAGE/learning-helper.png"

tar -czf "$OUTPUT" -C "$STAGE_ROOT" "LearningHelper-$VERSION"
echo "Pacote por usuário gerado em $OUTPUT"
