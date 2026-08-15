# Instalar o Cantinho no Windows

Este guia é para quem nunca instalou um programa assim. Não precisa saber nada
de programação. São **cinco passos** e leva uns 15 minutos, sendo que a maior
parte é o computador trabalhando sozinho enquanto você espera.

Se em algum momento aparecer uma tela preta com muito texto correndo, está
tudo certo — é assim mesmo.

> **Com pressa e sem medo de errar?** Passos 1 e 2, depois abra a pasta
> `Documentos\cantinho-main`, dê **dois cliques** no arquivo `cantinho.bat`,
> digite **1** e aperte Enter. Os passos 3 e 4 são esse mesmo caminho
> explicado devagar.

---

## Passo 1 — Instalar o Python

O Cantinho é feito numa linguagem chamada Python, e o Windows não vem com ela.
É de graça e leva 3 minutos.

1. Abra o navegador e vá em **https://www.python.org/downloads/**
2. Clique no botão grande amarelo que diz **Download Python** (qualquer versão
   que aparecer serve).
3. Quando o arquivo terminar de baixar, clique nele para abrir.
4. **⚠️ ISTO É O MAIS IMPORTANTE DO GUIA:** na primeira tela do instalador, lá
   embaixo, tem uma caixinha escrita **"Add python.exe to PATH"**.
   **Marque essa caixinha antes de continuar.** Se você esquecer, nada mais vai
   funcionar e vamos ter que começar de novo.
5. Clique em **Install Now** e espere.
6. Quando terminar, clique em **Close**.

---

## Passo 2 — Baixar o Cantinho

1. Abra o navegador e vá em **https://github.com/igormahall/cantinho**
2. Procure um botão verde escrito **`< > Code`** e clique nele.
3. No menuzinho que abrir, clique em **Download ZIP**.
4. O arquivo `cantinho-main.zip` vai para a pasta **Downloads**.

Agora precisamos tirar as coisas de dentro desse zip e pôr no lugar certo:

5. Abra a pasta **Downloads** (no Explorador de Arquivos, aquele ícone de
   pastinha amarela na barra de tarefas).
6. Clique **com o botão direito** no arquivo `cantinho-main.zip`.
7. Escolha **Extrair tudo...**
8. Vai abrir uma janela perguntando onde extrair. Apague o que estiver escrito
   lá e escreva exatamente isto:

   ```
   %USERPROFILE%\Documents
   ```

9. **Desmarque** a caixinha "Mostrar arquivos extraídos quando concluído", se
   ela estiver marcada.
10. Clique em **Extrair** e espere.

Pronto: agora existe uma pasta chamada `cantinho-main` dentro de
**Documentos**.

---

## Passo 3 — Abrir a tela preta (o Prompt de Comando)

1. Segure a tecla **Windows** (aquela com a janelinha, entre o Ctrl e o Alt) e,
   sem soltar, aperte a tecla **R**. Solte as duas.
2. Vai aparecer uma janelinha pequena no canto de baixo escrita **Executar**.
3. Escreva `cmd` e aperte **Enter**.

Abriu uma janela preta com letras brancas. É por aqui que continuamos.

> **Dica:** nessa janela preta, o atalho para colar texto é **Ctrl + V**, e para
> copiar é **Ctrl + C**, igual em todo lugar. Você pode copiar os comandos deste
> guia e colar lá — é bem mais seguro do que digitar.

---

## Passo 4 — Ir até a pasta e montar o programa

Você vai colar **dois comandos**, um de cada vez. Depois de colar cada um,
aperte **Enter** e **espere ele terminar** antes de ir para o próximo.

Você sabe que um comando terminou quando a tela para de andar e aparece de
novo uma linha começando com `C:\...>` esperando você digitar.

### Comando 1 — entrar na pasta do Cantinho

```
cd /d "%USERPROFILE%\Documents\cantinho-main"
```

Se aparecer **"O sistema não pode encontrar o caminho especificado"**, a pasta
não está onde deveria. Volte ao Passo 2 e confira se você extraiu para
`%USERPROFILE%\Documents`.

### Comando 2 — instalar

```
cantinho.bat instalar
```

Este é o demorado: uns 5 a 10 minutos. Vai passar MUITO texto na tela, com
palavras como "Downloading" e "Installing". É normal. Vá tomar um café.

No fim ele escreve:

```
atalho criado: C:\Users\...\Cantinho.lnk

 Pronto. O atalho "Cantinho" esta na Area de Trabalho, e o duplo clique
 nele ja abre o app - nao ha mais nenhum comando para rodar depois.
```

E é isso mesmo: **não há um terceiro comando.**

---

## Passo 5 — Abrir

Feche a janela preta (pode clicar no X).

Olhe para a Área de Trabalho: tem um ícone novo com uma **plantinha** escrito
**Cantinho**. Dê dois cliques nele.

Na primeira vez que abrir, uma plantinha vai aparecer na tela e explicar o
programa em sete telinhas. É só ir clicando em **próximo**. Se quiser rever
depois, é em **"o quarto" → "o passeio"**.

**É isso. Bom trabalho. 🌱**

---

## Quando sair uma versão nova

Quem fez o programa vai avisar quando tiver novidade. Atualizar leva 3 minutos
e **não apaga nada do que você anotou** — as suas coisas ficam guardadas em
outro lugar, separado do programa.

### 1. Baixe os arquivos novos

Do mesmo jeito do Passo 2 lá em cima: **github.com/igormahall/cantinho** →
botão verde **`<> Code`** → **Download ZIP** → botão direito no arquivo →
**Extrair tudo…** → cole `%USERPROFILE%\Documents` como destino.

O Windows vai perguntar se você quer substituir os arquivos que já existem.
**Diga que sim, substituir tudo.**

### 2. Rode um comando só

Abra a tela preta (<kbd>Windows</kbd> + <kbd>R</kbd> → `cmd` → Enter) e cole
os dois comandos, um de cada vez:

```
cd /d "%USERPROFILE%\Documents\cantinho-main"
```

```
cantinho.bat atualizar
```

Espere terminar. Pronto — abra pelo atalho de sempre.

**Não precisa fechar o Cantinho antes.** Se ele estiver aberto, a atualização
fecha sozinha — inclusive o ícone que fica perto do relógio. Se tinha um
cronômetro correndo, ele é guardado até o último minuto registrado, e o próprio
app avisa disso quando você abrir de novo.

> **Se você souber usar git:** dá para pular o item 1 inteiro. Numa pasta que
> veio de `git clone`, o `cantinho.bat atualizar` pergunta se pode puxar as
> novidades do GitHub e faz isso sozinho.

---

## Se der errado

### "cantinho.bat não é reconhecido como um comando interno ou externo"
Você não está na pasta certa. Cole o Comando 1 de novo e confira se não sobrou
nenhum erro.

### "Nao encontrei o Python" (aparece logo depois do Comando 2)
O Python não foi instalado, ou a caixinha **"Add python.exe to PATH"** não foi
marcada no Passo 1. A solução é desinstalar o Python (Iniciar → "Adicionar ou
remover programas" → procure Python → Desinstalar) e refazer o Passo 1 com
muita atenção à caixinha.

### Não apareceu o atalho na Área de Trabalho
Dê dois cliques no `cantinho.bat` e escolha a opção **2** (atualizar). Ela
refaz o atalho no fim, e é rápida — o ambiente já está instalado.

### O ícone existe, mas o duplo clique nele não faz nada
Se você instalou este programa **antes** de agosto de 2026, o atalho antigo
aponta para um arquivo que o Windows recusa abrir, sem dizer nada a ninguém. A
versão de hoje não gera mais esse arquivo.

O conserto é a opção **1** (instalar) do `cantinho.bat`: ela apaga o que
sobrou, refaz tudo e cria o atalho novo. Suas anotações não são tocadas.

### O antivírus da empresa reclamou de alguma coisa
Não deveria mais acontecer: o programa não cria nenhum arquivo executável
próprio — o que abre é o Python oficial, assinado pela fundação que o
desenvolve. Se ainda assim reclamar, o
[plataformas.md](plataformas.md) tem o que mandar para quem administra a
máquina.

### Fechei a janela do Cantinho e ele sumiu
Ele não fecha de verdade quando você fecha a janela — fica esperando perto do
relógio, no canto de baixo à direita. Clique na setinha `^` lá e procure a
plantinha. Para fechar de vez: **"o quarto" → "sair"**.

### Quero apagar tudo
Dê dois cliques no `cantinho.bat` e escolha a opção **4** (remover). Ela tira o
atalho e todo o material que a instalação criou, e no fim pergunta,
**separadamente**, se as suas anotações também devem ir embora.

Essa segunda pergunta pede que você escreva a palavra `apagar` — qualquer outra
coisa deixa as anotações onde estão. É de propósito: elas são a única coisa que
não dá para refazer, e não existe cópia em lugar nenhum.

Se você respondeu que elas ficam e mudou de ideia depois, elas estão em
`%APPDATA%\Cantinho`. Se um dia quiser o Cantinho de volta com tudo o que
escreveu, é só instalar de novo — ele encontra as anotações no mesmo lugar.

Sobra a pasta `cantinho-main` dentro de Documentos, que é só o código. Arraste
para a lixeira e acabou.

---

## Um jeito ainda mais fácil (sem a tela preta)

Se você não gostou da janela preta, dá para fazer tudo clicando:

1. Abra a pasta `Documentos\cantinho-main`.
2. Dê dois cliques no arquivo **`cantinho.bat`**.
3. Vai abrir um menuzinho. Digite **1** e aperte Enter (é o "instalar"). Espere
   terminar.

Pronto, mesma coisa — inclusive o atalho na Área de Trabalho. Quando sair uma
versão nova, é o mesmo caminho com a opção **2**.
