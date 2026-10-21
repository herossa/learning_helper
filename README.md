# learning_helper

App de fundo que, de tempos em tempos, cobre a tela do computador com um desafio curto. Feito para uma criança de 9 anos: layout previsível, enunciado em português e dificuldade que sobe ou desce conforme a taxa de acerto.

- 5 módulos: cores, contas, problemas, perguntas e leitura
- Intervalo adaptativo entre 1 e 5 minutos, ajustado pelas respostas
- Tela de configurações na primeira execução e depois pelo atalho/CLI
- Estatísticas no navegador (tentativas, acertos, níveis e evolução)
- Lembrete de banheiro a cada 30 minutos, bloqueando a tela por 1 minuto
- Instalação por usuário, sem root, no Windows e no Linux
- Dados guardados só na máquina, em SQLite

## Instalação

Os pacotes ficam nas [releases do GitHub](https://github.com/herossa/learning_helper/releases). Todos instalam **apenas para o usuário atual**, sem pedir senha de administrador, e **preservam o banco de dados ao desinstalar**.

Cada release publica também um `SHA256SUMS` para conferir a integridade dos arquivos baixados:

```bash
sha256sum -c SHA256SUMS          # Linux, na pasta dos downloads
```

```powershell
Get-FileHash .\LearningHelper* -Algorithm SHA256   # Windows, compare com o SHA256SUMS
```

### Windows 10/11 (x64)

Baixe `LearningHelper-<versão>-Setup.exe` e execute. O instalador não é assinado digitalmente, então o SmartScreen pode avisar: clique em **Mais informações → Executar assim mesmo**.

O instalador:

- instala em `%LOCALAPPDATA%\Programs\LearningHelper` por padrão;
- oferece a opção de instalar para todos os usuários (requer administrador);
- cria atalhos no menu Iniciar para o app, **Configurações** e **Estatísticas**, e, se você quiser, na área de trabalho;
- pode iniciar junto com o Windows, **somente para o usuário atual** (caixa marcada por padrão, pode ser desmarcada).

Para desinstalar, use **Configurações → Aplicativos → Learning Helper** (ou o atalho "Desinstalar" no menu Iniciar). O banco e os logs em `%LOCALAPPDATA%\learning_helper` são mantidos; apague essa pasta manualmente para remover tudo.

Para habilitar ou desabilitar o autostart depois, pressione `Win+R`, digite `shell:startup` e adicione/remova o atalho "Learning Helper" dessa pasta. As demais opções ficam no atalho **Configurações do Learning Helper**.

### Linux (x86_64)

Há dois formatos: **AppImage** (arquivo único, não instala nada no sistema) e **pacote tar.gz** com instalador por usuário.

#### AppImage

```bash
chmod +x LearningHelper-<versão>-x86_64.AppImage   # o download não mantém a permissão de execução
./LearningHelper-<versão>-x86_64.AppImage
```

O banco e os logs continuam em `~/.local/share/learning_helper`. Para iniciar junto com a sessão:

```bash
./LearningHelper-<versão>-x86_64.AppImage --enable-autostart
./LearningHelper-<versão>-x86_64.AppImage --disable-autostart
```

O autostart guarda o caminho absoluto do AppImage. Se mover o arquivo, rode `--enable-autostart` de novo. Em sistemas sem FUSE, use `--appimage-extract-and-run`.

#### Pacote tar.gz (instalação por usuário)

```bash
tar -xzf LearningHelper-<versão>-linux-x86_64.tar.gz
cd LearningHelper-<versão>
./install-user.sh                  # instala em ~/.local
./install-user.sh --autostart      # instala e habilita o autostart
./install-user.sh --prefix ~/opt   # outro prefixo de instalação
```

O instalador copia o app para `~/.local/opt/learning-helper`, cria o comando `~/.local/bin/learning-helper`, os atalhos **Learning Helper**, **Configurações** e **Estatísticas** no menu de aplicativos e o ícone. O atalho principal também oferece ações rápidas de configurações e estatísticas. Adicione `~/.local/bin` ao `PATH` se ainda não estiver. Depois de instalar, a pasta extraída pode ser apagada.

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

Para alternar o autostart depois:

```bash
~/.local/bin/learning-helper --enable-autostart
~/.local/bin/learning-helper --disable-autostart
```

## Como funciona

O intervalo é adaptativo: por padrão, entre **1 e 5 minutos**, começando em **3 minutos**; cada resposta certa soma 30 segundos e cada resposta errada subtrai 30 segundos, sempre respeitando os limites. Esses valores, os limiares de nível e o feedback são configuráveis. Depois de responder há um feedback curto ("Certo!" ou "Quase! Olhe com calma da próxima vez.") e o computador é liberado.

Na **primeira execução**, a tela de configurações aparece antes de qualquer desafio. O primeiro desafio só é agendado depois do intervalo configurado (3 minutos por padrão); fechar a tela sem salvar usa os padrões e marca a configuração como concluída.

Módulos, nesta ordem, desbloqueados pela taxa de acerto:

1. Cores
2. Contas
3. Problemas
4. Perguntas
5. Leitura

Os problemas usam as mesmas operações de contas (soma, subtração e multiplicação, conforme o nível), mas em histórias curtas com nomes e objetos sorteados. Nunca aparecem números negativos: na subtração o total é sempre maior ou igual ao que sai, e as alternativas erradas também são sempre não negativas.

Começa só com cores, no nível 1. A cada 10 tentativas de um módulo (valor configurável):

- ≥ 80% de acerto: sobe o nível (máximo 5); se esse for o módulo mais novo liberado, desbloqueia o seguinte
- ≤ 40% de acerto: desce o nível (mínimo 1); módulo já aberto não some

Os limiares e o nível máximo também podem ser mudados em Configurações. Módulos desativados não são escolhidos e são pulados no desbloqueio; o progresso deles fica guardado para quando forem religados.

Cada resposta da criança é gravada em SQLite: teste (`module_id`), enunciado, opções, gabarito e o que foi respondido.

## Configurações

A tela de configurações aparece automaticamente na primeira execução e pode ser aberta depois de duas formas:

- atalho **Configurações do Learning Helper** no menu Iniciar (Windows) ou no menu de aplicativos (Linux);
- comando `learning-helper --settings` (ou `uv run python -m learning_helper --settings` no código-fonte).

O que pode ser ajustado:

- intervalo inicial, mínimo, máximo e passo por resposta;
- janela de avaliação, limiares de desbloqueio/nível e nível máximo;
- duração do feedback;
- duração da pausa do adulto;
- lembrete de banheiro (ligado/desligado, intervalo e duração);
- módulos ativos (Cores, Contas, Problemas, Perguntas e Leitura);
- autostart no Linux.

A seção **Dados** mostra o caminho do banco e abre a pasta onde ficam o banco e os logs. As mudanças valem no próximo início do app (com exceção do intervalo inicial, aplicado ao salvar a primeira configuração de um perfil novo). Fechar a janela no modo normal cancela; **Restaurar padrões** preenche os campos com os valores originais. Desativar um módulo não apaga níveis nem tentativas.

## Estatísticas

O atalho **Estatísticas do Learning Helper** (ou `learning-helper --stats`) abre um painel no navegador, servido localmente:

- indicadores de tentativas, acertos, precisão e dias ativos;
- tentativas e precisão por dia;
- resumo por módulo, com nível atual e status (liberado, bloqueado ou desativado);
- precisão por nível;
- últimas 100 tentativas, com enunciado, resposta e gabarito;
- filtros de período (7, 30, 90 dias ou tudo) e de módulos.

O painel abre uma janela pequena com **Encerrar**; fechá-la desliga o servidor local. A leitura é feita em modo somente leitura, então ver as estatísticas não altera níveis, tentativas ou configurações. O Streamlit vai incluído nos instaladores.

## Atalho do adulto

`Control+Alt+Shift+P` fecha o desafio **sem gravar tentativa** e pausa novos bloqueios por **30 minutos**. Não aparece na tela da criança. Esc e Alt+F4 não fecham o desafio.

## Lembrete de banheiro

A cada **30 minutos** aparece um aviso de banheiro que bloqueia a tela por **1 minuto**, com uma imagem e uma contagem regressiva. Não há nada para responder: ele fecha sozinho ao fim da contagem.

- É independente dos desafios: não mexe em níveis, desbloqueio nem no histórico de tentativas.
- Se um desafio estiver na tela, o lembrete espera o desafio terminar (e o desafio também espera o lembrete sair).
- Durante a pausa do adulto, o lembrete também fica em espera.
- `Control+Alt+Shift+P` fecha o lembrete na hora e mantém a pausa de 30 minutos.

O lembrete vem **ligado** por padrão e o intervalo/duração podem ser mudados em Configurações. Para desligar (ou religar) pelo terminal:

```bash
learning-helper --disable-bathroom-reminder
learning-helper --enable-bathroom-reminder
```

## Dados locais

Banco:

- Linux: `~/.local/share/learning_helper/learning_helper.db`
- Windows: `%LOCALAPPDATA%\learning_helper\learning_helper.db`

Logs (rotativos, até 1 MB + 2 backups):

- Linux: `~/.local/share/learning_helper/app.log`
- Windows: `%LOCALAPPDATA%\learning_helper\app.log`

O painel de estatísticas grava a saída do servidor local em `stats.log`, na mesma pasta.

Na mesma pasta há um `app.lock`, usado para impedir duas cópias do app ao mesmo tempo. Outro caminho para o banco:

```bash
uv run python -m learning_helper --db /caminho/arquivo.db
```

## Solução de problemas

- **AppImage: "Permission denied"** — o download não mantém a permissão de execução; rode `chmod +x LearningHelper-<versão>-x86_64.AppImage`.
- **AppImage não abre por falta de FUSE** — rode com `--appimage-extract-and-run`.
- **Nada acontece ao abrir o app de novo** — é a trava de instância única: a segunda cópia detecta o `app.lock` e encerra sem abrir outra janela.
- **O overlay não aparece** — pode ser a pausa do adulto ativa (30 minutos), o primeiro intervalo ainda contando ou a instância antiga ainda rodando.
- **As estatísticas não abrem** — veja o `stats.log` na mesma pasta; o servidor usa uma porta local aleatória e o navegador padrão.
- **Windows: aviso do SmartScreen** — o instalador não é assinado; use **Mais informações → Executar assim mesmo**.
- **Erros silenciosos** — veja o `app.log` em `Dados locais` acima.

## Desenvolvimento

### Requisitos

- Python 3.11+ (o repositório fixa a 3.11 em `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Linux ou Windows 10/11

### Como rodar

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

### Opções de linha de comando

```text
--version                     mostra a versão e sai
--self-check                  valida recursos empacotados (schema, bancos, imagem e Streamlit) e sai
--settings                    abre a tela de configuração e sai
--stats                       abre as estatísticas no navegador
--debug                       intervalo curto e botão de fechar no overlay
--db CAMINHO                  usa outro arquivo SQLite
--enable-autostart            inicia com o usuário atual (Linux)
--disable-autostart           remove o autostart do usuário (Linux)
--enable-bathroom-reminder    liga o lembrete de banheiro (padrão)
--disable-bathroom-reminder   desliga o lembrete de banheiro
```

No Windows o autostart é gerenciado pelo instalador; as duas opções de autostart apenas avisam isso e não alteram nada. As opções do lembrete de banheiro valem em qualquer plataforma e gravam a preferência no banco.

### Testes

```bash
uv run pytest
```

Os testes cobrem o motor adaptativo, os geradores de desafio, o SQLite e a migração de configurações, a escolha de diretório/geometria por plataforma, o CLI, o autostart, a trava de instância, as consultas de estatísticas e o painel Streamlit (via `AppTest`). A UI Tk fica de fora da suíte por padrão; para os testes de fumaça da janela e da tela de configurações (precisam de desktop), rode:

```bash
RUN_GUI_TESTS=1 uv run pytest tests/test_overlay_smoke.py
```

O CI (GitHub Actions) roda a suíte em Linux e Windows, e o workflow `package` valida os instaladores.

### Estrutura

```text
src/learning_helper/
├── app.py               # CLI, logging, self-check, primeira execução e instância única
├── settings.py          # preferências, validação e padrões
├── autostart.py         # entrada .desktop por usuário (Linux)
├── single_instance.py   # trava de arquivo multiplataforma
├── reminders.py         # cálculo do lembrete de banheiro (sem Tk)
├── config.py            # constantes padrão e configuração de execução
├── adaptive/            # motor adaptativo (níveis, desbloqueio, intervalo)
├── challenges/          # geradores e bancos JSON (perguntas, leitura)
├── overlay/             # UI Tk/customtkinter, configurações e geometria
├── stats/               # consultas somente leitura + painel Streamlit
└── persistence/         # SQLite e schema.sql
packaging/               # PyInstaller, Inno Setup, AppImage, tar.gz e ícone
tests/
```

## Gerar os pacotes

A versão tem uma única fonte: `__version__` em `src/learning_helper/__init__.py` (lida pelo Hatch via `pyproject.toml`).

### Linux

```bash
uv sync --frozen --group dev
uv run pyinstaller packaging/learning-helper.spec --noconfirm

# AppImage (precisa do appimagetool no PATH ou em APPIMAGETOOL)
APPIMAGETOOL=appimagetool packaging/linux/build-appimage.sh 0.4.0

# pacote por usuário com install/uninstall
packaging/linux/build-user-tarball.sh 0.4.0

# teste de instalação/desinstalação em HOME temporário
packaging/linux/test-user-install.sh dist/LearningHelper-0.4.0-linux-x86_64.tar.gz
```

Saídas em `dist/`: `LearningHelper-<versão>-x86_64.AppImage` e `LearningHelper-<versão>-linux-x86_64.tar.gz`.

Se o `appimagetool` for o próprio AppImage, rode:

```bash
APPIMAGETOOL=./appimagetool-x86_64.AppImage \
APPIMAGETOOL_ARGS=--appimage-extract-and-run \
packaging/linux/build-appimage.sh 0.4.0
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

A imagem do lembrete de banheiro (`src/learning_helper/overlay/bathroom.png`) segue a mesma ideia e é gerada por `packaging/make_bathroom_image.py`:

```bash
uv run python packaging/make_bathroom_image.py
```

## Release

O workflow `.github/workflows/package.yml` roda em PRs e pushes que mexem em `src/`, `packaging/` ou dependências. Para publicar:

```bash
git tag v0.4.0
git push origin v0.4.0
```

O job de release confere se a tag (`v0.4.0`) bate com `__version__` (`0.4.0`) e publica no GitHub um instalador Windows, um AppImage, o tar.gz por usuário e o `SHA256SUMS`.
