# Instalar o Cantinho no Windows

Este guia é para quem nunca instalou um programa assim. Não precisa saber nada
de programação. São **cinco passos** e leva uns 15 minutos, sendo que a maior
parte é o computador trabalhando sozinho enquanto você espera.

Se em algum momento aparecer uma tela preta com muito texto correndo, está
tudo certo — é assim mesmo.

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

Você vai colar **três comandos**, um de cada vez. Depois de colar cada um,
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

### Comando 2 — preparar tudo

```
cantinho.bat instalar
```

Este é o demorado: uns 5 a 10 minutos. Vai passar MUITO texto na tela, com
palavras como "Downloading" e "Installing". É normal. Vá tomar um café.

Quando terminar, vai aparecer **`Ambiente pronto.`** e a janela volta a esperar
você digitar.

### Comando 3 — criar o programa e o atalho

```
cantinho.bat empacotar
```

Mais uns 2 minutos. No fim ele escreve:

```
Pronto: C:\Users\...\dist\Cantinho\Cantinho.exe
atalho criado: C:\Users\...\Cantinho.lnk
```

Essas duas linhas querem dizer que deu tudo certo, **e que o atalho já está na
sua Área de Trabalho**.

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

### 1. Feche o Cantinho de verdade

Não basta fechar a janela: ele fica esperando perto do relógio, no canto de
baixo à direita. Use **"o quarto" → "sair"**.

(Se esquecer, o computador avisa: vai aparecer uma mensagem dizendo que o
Cantinho está aberto. Aí é só fechar e rodar de novo.)

### 2. Baixe os arquivos novos

Do mesmo jeito do Passo 2 lá em cima: **github.com/igormahall/cantinho** →
botão verde **`<> Code`** → **Download ZIP** → botão direito no arquivo →
**Extrair tudo…** → cole `%USERPROFILE%\Documents` como destino.

O Windows vai perguntar se você quer substituir os arquivos que já existem.
**Diga que sim, substituir tudo.**

### 3. Rode um comando só

Abra a tela preta (<kbd>Windows</kbd> + <kbd>R</kbd> → `cmd` → Enter) e cole
os dois comandos, um de cada vez:

```
cd /d "%USERPROFILE%\Documents\cantinho-main"
```

```
cantinho.bat atualizar
```

Espere terminar. Pronto — abra pelo atalho de sempre.

> **Se você souber usar git:** dá para trocar o passo 2 inteiro por um comando.
> Na pasta do Cantinho, rode `git pull` antes do `cantinho.bat atualizar`. Só
> funciona se você tiver baixado com `git clone` em vez do ZIP.

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

### O antivírus apagou o `Cantinho.exe`
Acontece em computador de empresa, e não é vírus: o programinha que "embrulha"
o app é o mesmo em milhares de programas, inclusive nos ruins, então alguns
antivírus apagam todos por precaução.

Existe uma versão que não tem esse problema. Rode este comando no lugar do
Comando 3:

```
cantinho.bat portatil
```

Ele gera um arquivo `Cantinho-portatil-windows.zip` dentro da pasta. Extraia
esse zip onde quiser e clique no `Cantinho.bat` de dentro dele.

### Não apareceu o atalho na Área de Trabalho
Rode este comando na janela preta, dentro da pasta do Cantinho:

```
cantinho.bat atalho
```

Se mesmo assim não aparecer, o programa continua funcionando: ele está em
`Documentos\cantinho-main\dist\Cantinho\Cantinho.exe` e você pode clicar nele
direto (ou arrastar para a Área de Trabalho segurando Alt).

### Fechei a janela do Cantinho e ele sumiu
Ele não fecha de verdade quando você fecha a janela — fica esperando perto do
relógio, no canto de baixo à direita. Clique na setinha `^` lá e procure a
plantinha. Para fechar de vez: **"o quarto" → "sair"**.

### Quero apagar tudo
Apague a pasta `cantinho-main` de dentro de Documentos, e arraste o atalho da
Área de Trabalho para a lixeira. O programa não deixa nada em outro lugar
além de um arquivinho com as suas anotações em
`%APPDATA%\Cantinho` — apague essa pasta também se quiser sumir com tudo.

---

## Um jeito ainda mais fácil (sem a tela preta)

Se você não gostou da janela preta, dá para fazer tudo clicando:

1. Abra a pasta `Documentos\cantinho-main`.
2. Dê dois cliques no arquivo **`cantinho.bat`**.
3. Vai abrir um menuzinho com números. Digite **1** e aperte Enter (é o
   "instalar"). Espere terminar.
4. Dê dois cliques no `cantinho.bat` de novo, digite **3** e aperte Enter (é o
   "gerar o executável"). Espere terminar.

Pronto, mesma coisa — inclusive o atalho na Área de Trabalho.
