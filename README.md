# learning_helper

App de fundo que, de tempos em tempos, cobre a tela do computador com um desafio curto. Feito para uma criança de 9 anos: layout previsível, enunciado em português e dificuldade que sobe ou desce conforme a taxa de acerto.

## Instalação

Os pacotes ficam nas [releases do GitHub](https://github.com/herossa/learning_helper/releases). Todos instalam **apenas para o usuário atual**, sem pedir senha de administrador, e preservam o banco de dados ao desinstalar.

### Windows 10/11

Baixe `LearningHelper-<versão>-Setup.exe` e execute. O instalador:

- instala em `%LOCALAPPDATA%\Programs\LearningHelper` por padrão;
- oferece a opção de instalar para todos os usuários (requer administrador);
- cria atalho no menu Iniciar e, opcionalmente, na área de trabalho;
- pode iniciar junto com o Windows, **somente para o usuário atual** (caixa marcada por padrão; pode ser desmarcada).

Para desinstalar, use **Configurações → Aplicativos → Learning Helper** (ou o atalho "Desinstalar" no menu Iniciar). O banco e os logs em `%LOCALAPPDATA%\learning_helper` são mantidos; apague essa pasta manualmente para remover tudo.

Para habilitar ou desabilitar o autostart depois:

```powershell
# habilita: atalho em shell:startup
shell:startup
# remova o atalho "Learning Helper" dessa pasta para desabilitar
```

### Linux

Há dois formatos: **AppImage** (arquivo único, não instala nada no sistema) e **pacote tar.gz** com instalador por usuário.

#### AppImage

```bash
chmod +x LearningHelper-<versão>-x86_64.AppImage
./LearningHelper-<versão>-x86_64.AppImage
```

O banco e os logs continuam em `~/.local/share/learning_helper`. Para iniciar junto com a sessão:

```bash
./LearningHelper-<versão>-x86_64.AppImage --enable-autostart
./LearningHelper-<versão>-x86_64.AppImage --disable-autostart
```

O autostart guarda o caminho absoluto do AppImage. Se mover o arquivo, rode `--enable-autostart` de novo.

#### Pacote tar.gz (instalação por usuário)

```bash
tar -xzf LearningHelper-<versão>-linux-x86_64.tar.gz
cd LearningHelper-<versão>
./install-user.sh                 # instala em ~/.local
./install-user.sh --autostart     # instala e habilita o autostart
```

O instalador copia o app para `~/.local/opt/learning-helper`, cria o comando `~/.local/bin/learning-helper`, o atalho no menu de aplicativos e o ícone. Adicione `~/.local/bin` ao `PATH` se ainda não estiver.

Desinstalar (preserva banco e logs):

```bash
~/.local/bin/learning-helper-uninstall
# ou, se o script ainda estiver na pasta extraída:
./uninstall-user.sh
```

Para remover também banco e logs:

```bash
~/.local/bin/learning-helper-uninstall --purge
# ou: ./uninstall-user.sh --purge
```

Use `--prefix DIR` no `install-user.sh` para instalar em outro prefixo (o padrão é `~/.local`).

Para habilitar/desabilitar o autostart depois:

```bash
~/.local/bin/learning-helper --enable-autostart
~/.local/bin/learning-helper --disable-autostart
```

## Requisitos (desenvolvimento)

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

Funciona em Linux e Windows 10/11.

## Como rodar

Linux:

```bash
uv sync --group dev
uv run learning-helper
```

Windows (PowerShell):

```powershell
uv sync --group dev
uv run learning-helper
```

`learning-helper` usa o launcher gráfico: no Windows abre **sem janela de console**. Para acompanhar erros no terminal, use `uv run python -m learning_helper`.

Modo desenvolvimento (intervalo de 10 segundos e botão `close` no overlay):

```bash
uv run python -m learning_helper --debug
```

## Opções de linha de comando

```text
--version             mostra a versão e sai
--self-check          valida recursos empacotados (schema e bancos) e sai
--debug               intervalo curto e botão de fechar no overlay
--db CAMINHO          usa outro arquivo SQLite
--enable-autostart    inicia com o usuário atual (Linux)
--disable-autostart   remove o autostart do usuário (Linux)
```

No Windows o autostart é gerenciado pelo instalador; essas duas últimas opções avisam isso e não alteram nada.

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

## Dados locais

Banco:

- Linux: `~/.local/share/learning_helper/learning_helper.db`
- Windows: `%LOCALAPPDATA%\learning_helper\learning_helper.db`

Logs (rotativos, até 1 MB + 2 backups):

- Linux: `~/.local/share/learning_helper/app.log`
- Windows: `%LOCALAPPDATA%\learning_helper\app.log`

Outro caminho para o banco:

```bash
uv run python -m learning_helper --db /caminho/arquivo.db
```

O app usa uma trava de instância única: abrir de novo apenas foca/ignora a segunda cópia, sem duplicar janelas.

## Atalho do adulto

`Control+Alt+Shift+P` fecha o desafio **sem gravar tentativa** e pausa novos bloqueios por **30 minutos**. Não aparece na tela da criança. Esc e Alt+F4 não fecham o desafio.

## Testes

```bash
uv run pytest
```

Os testes cobrem o motor adaptativo, os geradores de desafio, o SQLite, a escolha de diretório/geometria por plataforma, o CLI, o autostart e a trava de instância. A UI Tk fica de fora da suíte por padrão; para um teste de fumaça da janela (precisa de desktop), rode:

```bash
RUN_GUI_TESTS=1 uv run pytest tests/test_overlay_smoke.py
```

O CI (GitHub Actions) roda a suíte em Linux e Windows, e o workflow `package` valida os instaladores.

## Gerar os pacotes

A versão tem uma única fonte: `__version__` em `src/learning_helper/__init__.py` (lida pelo Hatch via `pyproject.toml`).

### Linux

```bash
uv sync --frozen --group dev
uv run pyinstaller packaging/learning-helper.spec --noconfirm

# AppImage (precisa do appimagetool no PATH ou em APPIMAGETOOL)
APPIMAGETOOL=appimagetool packaging/linux/build-appimage.sh 0.2.0

# pacote por usuário com install/uninstall
packaging/linux/build-user-tarball.sh 0.2.0

# teste de instalação/desinstalação em HOME temporário
packaging/linux/test-user-install.sh dist/LearningHelper-0.2.0-linux-x86_64.tar.gz
```

Saídas em `dist/`: `LearningHelper-<versão>-x86_64.AppImage` e `LearningHelper-<versão>-linux-x86_64.tar.gz`.

Se o `appimagetool` for o próprio AppImage, rode:

```bash
APPIMAGETOOL=./appimagetool-x86_64.AppImage \
APPIMAGETOOL_ARGS=--appimage-extract-and-run \
packaging/linux/build-appimage.sh 0.2.0
```

### Windows

Com [Inno Setup 6](https://jrsoftware.org/isinfo.php) instalado (e `iscc` no PATH):

```powershell
uv sync --frozen --group dev
powershell -ExecutionPolicy Bypass -File packaging/windows/build.ps1
```

O script gera o version info, roda o PyInstaller, valida o executável com `--self-check` e gera `dist\installer\LearningHelper-<versão>-Setup.exe`.

### Ícone

O ícone é um placeholder gerado por `packaging/make_icon.py` (PNG 512 e ICO multi-tamanho em `packaging/icons/`). Os arquivos são commitados; para trocar a arte, edite o script e rode:

```bash
uv run python packaging/make_icon.py
```

### Release

O workflow `.github/workflows/package.yml` roda em PRs e pushes que mexem em `src/`, `packaging/` ou dependências. Para publicar:

```bash
git tag v0.2.0
git push origin v0.2.0
```

O job de release confere se a tag (`v0.2.0`) bate com `__version__` (`0.2.0`) e publica no GitHub um instalador Windows, um AppImage, o tar.gz por usuário e `SHA256SUMS`.
