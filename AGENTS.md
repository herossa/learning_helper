# Diretrizes do projeto

## Git: sempre trabalhar em branch

- Nunca altere, commite ou faça push diretamente na `main`.
- Antes de começar qualquer tarefa, atualize a `main` e crie uma branch descritiva:

  ```bash
  git switch main
  git pull
  git switch -c feat/nome-curto
  ```

- Use prefixos como `feat/`, `fix/`, `docs/`, `refactor/` ou `chore/`.
- Faça commits pequenos e com mensagens claras.
- Rode os testes antes de enviar a branch:

  ```bash
  uv run pytest -q
  ```

- Para mudanças de interface, rode também os testes de fumaça da UI:

  ```bash
  RUN_GUI_TESTS=1 uv run pytest tests/test_overlay_smoke.py -q
  ```

- Envie a branch e abra um pull request para a `main`:

  ```bash
  git push -u origin nome-da-branch
  gh pr create
  ```

- O merge para a `main` é feito somente por pull request, depois dos checks
  passarem: use a interface do GitHub ou `gh pr merge`.
- Depois do merge, atualize a `main` local e remova a branch:

  ```bash
  git switch main
  git pull
  git branch -d nome-da-branch
  ```

- Não use `--no-verify` para contornar o hook de proteção da `main` sem
  autorização explícita.

O fluxo completo e a proteção configurada no GitHub estão descritos em
[README.md](README.md#branches-e-pull-requests).
