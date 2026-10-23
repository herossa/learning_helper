# Atalhos de desenvolvimento. Rode `make` ou `make help` para listar os alvos.
SHELL := /bin/sh

VERSION ?= $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/learning_helper/__init__.py)
PORT ?= 8501
TARBALL := dist/LearningHelper-$(VERSION)-linux-x86_64.tar.gz

.DEFAULT_GOAL := help
.PHONY: help setup hooks run debug settings stats stats-server test test-gui check \
	self-check wheel build appimage tarball packages test-install clean

help: ## Mostra os comandos disponíveis
	@awk 'BEGIN {FS = ":.*## "; printf "Uso: make <alvo> [VARIAVEL=valor]\n\nAlvos:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Sincroniza as dependências de desenvolvimento
	uv sync --group dev

hooks: ## Ativa os hooks locais do git
	scripts/setup-git-hooks.sh

run: ## Abre o app
	uv run learning-helper

debug: ## Abre o app em modo desenvolvimento (intervalo curto)
	uv run python -m learning_helper --debug

settings: ## Abre a tela de configurações
	uv run python -m learning_helper --settings

stats: ## Abre as estatísticas no navegador
	uv run python -m learning_helper --stats

stats-server: ## Sobe só o servidor de estatísticas (PORT=8501)
	uv run python -m learning_helper --stats-server --stats-port $(PORT)

test: ## Roda a suíte de testes (ARGS="-k cli" para filtrar)
	uv run pytest -q $(ARGS)

test-gui: ## Roda os testes de fumaça da interface (precisa de desktop)
	RUN_GUI_TESTS=1 uv run pytest tests/test_overlay_smoke.py -q

check: test self-check ## Roda os testes e o self-check

self-check: ## Valida os recursos empacotados
	uv run python -m learning_helper --self-check

wheel: ## Gera a wheel em dist/
	uv build --wheel

build: ## Gera o executável com PyInstaller
	uv run pyinstaller packaging/learning-helper.spec --noconfirm

appimage: build ## Gera o AppImage (precisa do appimagetool)
	packaging/linux/build-appimage.sh $(VERSION)

tarball: build ## Gera o pacote tar.gz por usuário
	packaging/linux/build-user-tarball.sh $(VERSION)

packages: build appimage tarball ## Gera o executável, o AppImage e o tar.gz

test-install: tarball ## Testa instalação/desinstalação em HOME temporário
	packaging/linux/test-user-install.sh $(TARBALL)

clean: ## Remove artefatos de build e caches
	rm -rf build dist .pytest_cache
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
