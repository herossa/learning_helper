# Capturas de tela

Imagens geradas a partir do próprio app, com um banco de demonstração.

| Arquivo | Tela |
|---|---|
| [01-desafio-cores.png](01-desafio-cores.png) | Desafio de cores |
| [02-desafio-cores-diferentes.png](02-desafio-cores-diferentes.png) | Desafio de cores diferentes |
| [03-desafio-comparacao.png](03-desafio-comparacao.png) | Desafio de comparação |
| [04-desafio-contas.png](04-desafio-contas.png) | Desafio de contas |
| [05-desafio-problemas.png](05-desafio-problemas.png) | Desafio de problemas |
| [06-desafio-perguntas.png](06-desafio-perguntas.png) | Desafio de perguntas |
| [07-desafio-leitura.png](07-desafio-leitura.png) | Desafio de leitura |
| [08-feedback-certo.png](08-feedback-certo.png) | Feedback de acerto |
| [09-feedback-errado.png](09-feedback-errado.png) | Feedback de erro |
| [10-lembrete-banheiro.png](10-lembrete-banheiro.png) | Lembrete de banheiro |
| [11-configuracao-inicial-topo.png](11-configuracao-inicial-topo.png) | Primeira configuração (início) |
| [12-configuracao-inicial-fim.png](12-configuracao-inicial-fim.png) | Primeira configuração (fim) |
| [13-configuracoes-topo.png](13-configuracoes-topo.png) | Configurações (início) |
| [14-configuracoes-meio.png](14-configuracoes-meio.png) | Configurações (meio) |
| [15-configuracoes-fim.png](15-configuracoes-fim.png) | Configurações (fim) |
| [16-estatisticas-evolucao.png](16-estatisticas-evolucao.png) | Estatísticas: evolução |
| [17-estatisticas-modulos.png](17-estatisticas-modulos.png) | Estatísticas: módulos e níveis |
| [18-estatisticas-tentativas.png](18-estatisticas-tentativas.png) | Estatísticas: tentativas recentes |
| [19-janela-estatisticas.png](19-janela-estatisticas.png) | Janela do servidor de estatísticas |

Para gerar novamente, na raiz do repositório:

```bash
make screenshots
```

O script precisa de uma sessão gráfica. O painel Streamlit usa Firefox com
geckodriver; o Selenium é instalado de forma temporária pelo próprio comando.
Para gerar só um grupo:

```bash
make screenshots ONLY=configuracoes
```
