#!/bin/sh
# Ativa os hooks locais versionados em .githooks para este clone.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ ! -f "$ROOT/.githooks/pre-push" ]; then
    echo "Hook não encontrado em $ROOT/.githooks/pre-push." >&2
    exit 1
fi

chmod +x "$ROOT/.githooks/pre-push"
git -C "$ROOT" config --local core.hooksPath .githooks

echo "Hooks locais ativados (core.hooksPath=.githooks)."
echo "A branch main agora só recebe alterações via merge de pull request."
