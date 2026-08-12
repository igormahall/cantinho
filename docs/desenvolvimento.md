# Desenvolvimento

Com o venv ativado e a partir da raiz do repositório. Rode sempre com o Python
do venv — o `python` do PATH não tem PySide6.

```bash
pip install -r requirements-dev.txt
```

## Comandos

```bash
python -m cantinho.main         # abre o app a partir do código
python -m pytest                # 333 testes; no Windows 3 pulam, são de Linux
python tools/simular_uso.py     # percorre a interface clicando de verdade
python tools/check_svg.py       # rasteriza os SVGs em build/svg_check/
python tools/semear.py          # banco descartável com duas semanas de uso
python tools/gerar_audio.py     # regera os sons
python tools/gerar_icone.py     # regera o ícone do app
python tools/gerar_capturas.py  # regera as imagens do README
```

Para experimentar sem sujar seus dados:

```bash
python -m cantinho.main --db ./teste.db --log DEBUG
```

No Windows, `cantinho.bat` embrulha tudo isso num menu — veja
[windows.md](windows.md).

## Coisas que só se aprende errando

- **O `pytest` não cobre o QML.** Quem faz isso é o `simular_uso.py`: ele abre
  as janelas, cria tarefa, escolhe, roda sessão, conclui, arrasta, corrige
  texto, captura ideia, abre a semana e fecha o dia com mouse e teclado
  sintéticos; depois reabre o banco do zero e confere o log evento por evento.
  **Rode depois de mexer em qualquer `.qml`.**
- **Rode o `simular_uso.py` com a tela ligada.** Com o monitor apagado ou a
  sessão bloqueada, o Qt para de apresentar quadros e toda animação congela. O
  roteiro não acha os painéis e falha em cascata, como se a interface
  estivesse quebrada.
- **Não basta o exit code do `check_svg.py`.** Abra os PNGs em
  `build/svg_check/`: um SVG com feature não suportada renderiza vazio ou
  parcial sem que o Qt reclame.
- **Áudio, ícone e capturas são versionados prontos**, e os geradores são
  determinísticos. Uma mudança no `git status` depois de rodá-los significa
  que o código mudou, não que o resultado variou.
- **Para a suíte sem abrir janela**, `QT_QPA_PLATFORM=offscreen`. Nesse modo o
  Qt fica sem nenhuma família de fonte, então texto vira tofu em screenshot —
  para avaliar a UI de verdade, rode com a plataforma normal.

## Por dentro

Só existe uma tabela, `events`, e ela só recebe `INSERT`. Backlog, sessões,
estante, planta, mural e histórico não são guardados: são recalculados a
partir do log toda vez, por funções puras. Corrigir alguma coisa é acrescentar
um evento novo — inclusive renomear uma tarefa, que é um `task.renamed` e não
uma edição do que já passou.

Isso significa que o estado da tela nunca pode divergir do que está em disco,
e que apagar o arquivo de banco é a única forma de perder alguma coisa. É
também o que dá o mural de graça: "essa ideia virou tarefa" não é um campo que
muda, é um evento posterior apontando para a tarefa que nasceu.

```
cantinho/
  core/       events.py store.py projections.py clock.py schedule.py   (sem Qt)
  services/   scene.py timer.py audio.py hotkey.py tray.py graphics.py
              single_instance.py desktop_entry.py            (plataforma)
  backend.py  a fronteira entre o log e a interface
  ui/         Main.qml Mini.qml theme/ room/ panels/
```

O ícone é o próprio vaso do quarto, e na bandeja ele acompanha o crescimento
da planta. O som é sintetizado pela biblioteca padrão do Python, não gravado.
Os SVGs de cena têm camadas com os mesmos ids nos dois temas, o que deixa a
planta e a estante mudarem sem redesenhar o quarto.

## Duas máquinas, um repositório

O código sincroniza pelo GitHub; **os bancos de evento não sincronizam
nunca**. O `.venv/` é por máquina e não é versionado, então depois de trocar
de sistema refaça o `pip install -r requirements-dev.txt`.

```bash
git pull --rebase     # antes de começar
git push              # antes de desligar
```

Se o `git status` acusar o repositório inteiro como modificado sem diferença
real, foi a quebra de linha: o conserto é `git add --renormalize .`, não
commitar o ruído.

---

`CLAUDE.md` tem as regras de arquitetura em detalhe, incluindo o que
deliberadamente não se faz aqui e por quê.
