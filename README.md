# learning_helper

App de fundo que, de tempos em tempos, cobre a tela do computador com um desafio curto. Feito para uma criança de 9 anos: layout previsível, enunciado em português e dificuldade que sobe ou desce conforme a taxa de acerto.

## Requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Como rodar

```bash
uv sync --group dev
uv run python -m learning_helper
```

Modo desenvolvimento (intervalo de 10 segundos e botão `close` no overlay):

```bash
uv run python -m learning_helper --debug
```

## Como funciona

O intervalo é adaptativo: entre **1 e 5 minutos** (limites e passo em `src/learning_helper/config.py`). Começa em **3 minutos**; cada resposta certa soma 30 segundos e cada resposta errada subtrai 30 segundos, sempre respeitando os limites de 1 e 5 minutos. Depois de uma resposta há um feedback curto (certo/errado) e o computador é liberado.

Módulos, nesta ordem, desbloqueados pela taxa de acerto:

1. Cores
2. Contas
3. Problemas
4. Perguntas
5. Leitura

Os problemas usam as mesmas operações de contas (soma, subtração e multiplicação, conforme o nível), mas em histórias curtas com nomes e objetos sorteados. Nunca aparecem números negativos: na subtração o total é sempre maior ou igual ao que sai, e as alternativas erradas também são sempre não negativas.

Começa só com cores, no nível 1. A cada 10 tentativas de um módulo:

- ≥ 80% de acerto: sobe o nível (máximo 5) e, se for o módulo mais novo, desbloqueia o seguinte
- ≤ 40% de acerto: desce o nível (mínimo 1); módulo já aberto não some

Cada resposta da criança é gravada em SQLite: teste (`module_id`), enunciado, opções, gabarito e o que foi respondido.

## Banco local

Padrão no Linux:

`~/.local/share/learning_helper/learning_helper.db`

Outro caminho:

```bash
uv run python -m learning_helper --db /caminho/arquivo.db
```

## Atalho do adulto

`Control+Alt+Shift+P` fecha o desafio **sem gravar tentativa** e pausa novos bloqueios por **30 minutos**. Não aparece na tela da criança. Esc e Alt+F4 não fecham o desafio.

## Testes

```bash
uv run pytest
```

Os testes cobrem o motor adaptativo, os geradores de desafio e o SQLite. A UI Tk fica de fora da suíte.
