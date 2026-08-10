# O Cantinho no Linux

Três coisas que só aparecem aqui: bibliotecas de sistema que o Qt carrega em
runtime, o Anaconda desligando o OpenGL, e o atalho na grade de aplicativos.

## Bibliotecas de sistema

O PySide6 do PyPI traz o Qt inteiro, mas não as bibliotecas de que o Qt depende
para falar com o X11 e com o áudio. Numa Ubuntu 22.04 recém-instalada faltam
algumas, e a falha é sempre a mesma linha:

```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though
it was found.
```

O conjunto que resolve:

```bash
sudo apt install python3-venv python3-dev \
     libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
     libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
     libxkbcommon-x11-0 libegl1 libgl1 libdbus-1-3
```

`libxcb-cursor0` é a que mais falta: o Qt 6 passou a exigi-la e ela não vem no
desktop padrão do 22.04. Para descobrir o que ainda falta em vez de adivinhar,
`QT_DEBUG_PLUGINS=1 python -m cantinho.main`. Se o app abrir mudo, falta
`libpulse0`.

## Quando o Anaconda desliga o OpenGL

Com o ambiente `base` ativo, o `qt-main` do conda exporta
`QT_XCB_GL_INTEGRATION=none` em todo terminal — a partir de
`~/anaconda3/etc/conda/activate.d/qt-main_activate.sh`, e não do `.bashrc`.
`none` manda o Qt não carregar integração GL nenhuma, e o Qt Quick precisa de
uma.

**O app cuida disso sozinho**: remove a variável do próprio processo ao subir e
registra um aviso no log. Um valor deliberado (`xcb_glx`, `xcb_egl`) passa
intacto.

Fica documentado porque o sintoma imita o de biblioteca faltando e leva a
instalar pacote atrás de pacote sem nada mudar:

```
QXcbIntegration: Cannot create platform OpenGL context, neither GLX nor EGL
are enabled
```

O que separa os dois casos: aqui o `QT_DEBUG_PLUGINS=1` **nem chega a varrer** o
diretório `xcbglintegrations`; com `.so` ausente ele varre e falha ao carregar.

Para tirar a variável do shell de vez, `conda config --set auto_activate_base
false`. E crie o venv com o Python do sistema (`/usr/bin/python3.10 -m venv
.venv`): com o `base` ativo, o `python` do PATH é o do conda, e as bibliotecas
dele se sobrepõem às do sistema que o plugin `xcb` carrega.

## O atalho na grade de aplicativos

Na primeira abertura que não encontra um atalho, o app cria um — e depois disso
não toca mais no assunto. São dois arquivos em `~/.local/share`:
`applications/cantinho.desktop` e o ícone em `icons/hicolor/256x256/apps/`.

```bash
python tools/instalar_atalho.py             # cria, se ainda não houver
python tools/instalar_atalho.py --de-novo   # reescreve o que existe
python tools/instalar_atalho.py --remover   # apaga o atalho e o ícone
```

**Mudou o repositório de pasta? Rode `--de-novo`.** O `Exec=` guarda o caminho
absoluto do Python do venv, e o app nunca sobrescreve um atalho existente — é
essa recusa que impede um clone de teste de roubar o ícone do menu apontando
para si. Execuções com `--db` não criam atalho.

**Se o ícone se comportar como antes depois de uma correção**, o problema não
está no arquivo: o GNOME Shell guarda os atalhos em memória. A instalação já
chama `update-desktop-database`; quando não basta, `Alt+F2`, `r`, Enter recarrega
a interface no X11 — no Wayland, sair e entrar na sessão.

## Duas diferenças de comportamento

**O atalho global não funciona.** `Ctrl+Shift+I` é a única parte específica de
plataforma sem equivalente aqui: `create_hotkey()` devolve um no-op. A captura
de ideia continua no mural, com a janela à vista.

**A bandeja depende do desktop.** O GNOME não mostra ícone de bandeja sem a
extensão *AppIndicator and KStatusNotifierItem Support*, que vem instalada e às
vezes desligada. Isso importa porque fechar a janela **não** encerra o app.
Sem bandeja, o jeito de trazê-lo de volta é abrir de novo pelo terminal — a
trava de instância única mostra a janela que já existe. Para encerrar de
verdade, **o quarto → sair**.
