# Apresentação do Learning Helper

Arquivo: [learning-helper.pptx](learning-helper.pptx)

Prévia: [learning-helper.pdf](learning-helper.pdf)

Uma apresentação curta (10 slides) sobre a motivação, o funcionamento e os
cuidados do projeto. As imagens vêm de [`docs/screenshots`](../screenshots/) e
os números refletem o comportamento padrão do app.

## Abrir no Google Slides

1. No Google Drive, clique em **Novo → Upload de arquivo** e envie o `.pptx`.
2. Abra o arquivo com **Google Slides**.
3. Se quiser editá-lo como apresentação nativa, use **Arquivo → Salvar como
   Google Slides**.

As notas do apresentador vão junto no arquivo e podem ser abertas em
**Exibir → Mostrar notas do apresentador**.

## Roteiro

| # | Slide | Ideia principal |
|---|---|---|
| 1 | Capa | O que é o projeto e para quem ele existe |
| 2 | Motivação | Apoiar aprendizagem, rotina e autonomia sem sobrecarga |
| 3 | Como funciona | O ciclo curto: agendar, desafiar, responder, registrar e ajustar |
| 4 | Os módulos | Os sete tipos de desafio e o desbloqueio gradual |
| 5 | Adaptação | Níveis de 1 a 5, blocos de 10 tentativas e critérios de 80%/40% |
| 6 | Rotina | O lembrete de banheiro e a transição |
| 7 | Configurações | O que os adultos podem ajustar |
| 8 | Acompanhamento | As três abas do painel de estatísticas |
| 9 | Tecnologia | SQLite local, instalação por usuário e atualizações com SHA-256 |
| 10 | Fechamento | Aprender com previsibilidade e crescer com autonomia |

## Gerar novamente

Na raiz do repositório:

```bash
make apresentacao
```

O comando instala o `python-pptx` apenas durante a geração. Para escolher outro
arquivo de saída:

```bash
uv run --with python-pptx python scripts/build_presentation.py --out /tmp/deck.pptx
```

O script também gera as notas do apresentador. As imagens não são copiadas para
o repositório: são lidas de `docs/screenshots/` e embutidas no `.pptx`.

Para atualizar também a prévia em PDF (é preciso ter o LibreOffice instalado):

```bash
make apresentacao-pdf
```
