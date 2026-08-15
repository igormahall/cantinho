# Auditoria de 14/08/2026 — o que ficou

Leitura do núcleo, do backend, dos serviços e do QML, com o app rodando nos dois
temas. Medições feitas no Ubuntu, com o Python do venv.

**Os achados de bug (A), de usabilidade (B) e o plano estético (D) foram todos
implementados e saíram daqui.** O motivo de cada decisão foi para onde ele
serve de fato: junto do código que a tomou, em `CLAUDE.md` e nos comentários.
Este arquivo guarda o que sobrou — as direções, que não são pendências e
algumas das quais não devem ser feitas.

O que foi entregue, em resumo, para quem for procurar:

- **A1–A7** — limite da navegação da semana; a semana deixando de reprojetar o
  log a cada evento (301 ms → 82 ms, e zero com o painel fechado); escrita
  atômica da marca de vida; o ano no período; o campo `project` morto fora da
  tela; `endDay` perguntando o extra como as outras saídas de sessão.
- **B1–B5, D1** — tipografia própria (Inter e EB Garamond embutidas, escala de
  corpos no `Theme`, algarismos tabulares no cronômetro); cartão do mural com
  teto de linhas; pista de rolagem nas listas; foco de teclado navegável.
- **D2–D5** — o quarto desfocando atrás dos painéis; a gaveta em coordenada de
  cena e fora de cima do abajur; a barra virando duas ilhas; a estante com luz
  própria e o rótulo de cada objeto; vinheta e paralaxe.
- **C2 e C3** — a página: a exportação do diário, e com ela a regra de que o
  horizonte mais longo se responde com um artefato e não com um painel maior.
  Ver abaixo o que continua valendo como critério.
- **C4** — o cadeado na porta do merge. Não é sync; é a prova de que a opção
  continua aberta. Ver abaixo.

---

## As direções, e as regras que ficaram delas

### C1 · O quarto é a visualização, e ele ainda não cresceu

A arquitetura inteira aponta para isso: projeção pura, estante permanente,
planta por janela móvel. Mas o quarto tem hoje dois eixos de crescimento (cinco
estágios de planta, doze vagas de estante) e depois trava. O limite conhecido
"a estante comporta 12 objetos" não é teto de desenho — é a fronteira onde o app
para de responder ao uso.

A convergência natural é **o cômodo ganhar coisas com o tempo**: uma segunda
prateleira, um tapete, um quadro na parede, a vista da janela mudando de
estação. Tudo derivável do log, sem tabela nova, sem streak, sem número. É o
caminho que dispensa gráfico para sempre, porque o gráfico é o quarto.

**É a maior peça que falta**, e a única que pede arte nova — que é justamente o
que a torna cara e o que faz dela a próxima decisão de verdade, não a próxima
tarefa.

### C2 e C3 · A página — **feitas, e a regra que ficou**

As duas eram a mesma coisa vista de dois lados, e por isso saíram juntas.

C3 era a saída dos dados: um log pessoal de anos sem exportação é um refém.
C2 era a semana — o único painel com número somado e navegação temporal, e a
costura por onde este projeto viraria planilha, porque daqui todo pedido natural
("e o mês?", "e o ano?", "e comparado com a semana passada?") é um passo em
direção ao dashboard que o princípio de design recusa.

A resposta serve às duas: **o horizonte mais longo é uma página, não um painel
maior.** Ver mais que uma semana é gerar o diário daquele período e lê-lo como
texto, fora do app. **Não existe aba de mês, e não deve existir.** A diferença
não é de formato, é de natureza: um painel de mês seria mais tela no mesmo
lugar, com a mesma pressão de virar comparação; a página é um artefato que se
lê, se guarda e se fecha.

Dois critérios que continuam valendo para quem mexer nisso:

- **Markdown é por longevidade, não por gosto.** O ponto de uma saída de
  emergência é ser legível sem ferramenta nenhuma, daqui a dez anos, por quem
  não tem o app. HTML seria mais bonito e menos útil exatamente onde importa.
- **A página não é relatório.** Sem média, sem percentual, sem comparação de
  períodos — e a regra vale mais forte num arquivo do que numa tela, porque
  arquivo dura mais e número de cobrança impresso cobra por mais tempo. Há teste
  varrendo a página em busca dessas palavras.

Implementação em `core/export.py`, detalhes em `CLAUDE.md`.

### C4 · A porta que o `device_id` guarda — **com cadeado**

Sync está proibido e deve continuar. O que foi feito **não é sync**: é a garantia
de que a opção continua existindo.

Opção preservada por acidente é opção que se perde por acidente. Bastaria uma
projeção passar a filtrar por `device_id`, ou a ordem do log passar a depender de
quem escreveu, e a porta fecharia sem ninguém perceber — para se descobrir no dia
em que alguém precisasse dela.

`tests/test_merge.py` prova que juntar dois logs é comutativo e idempotente, que
nenhuma projeção olha o `device_id`, e que o desempate é por uuid. Se alguém
gastar a opção, esses testes ficam vermelhos.

**A regra que continua:** nenhuma decisão nova deveria depender de o log ser de
uma máquina só.

---

## O que a auditoria ensinou sobre auditar este projeto

Fica registrado porque vale para a próxima:

- **O que não é exercitado não é testado, e o padrão decide isso sozinho.** O
  roteiro do QML rodava no tema `auto`, que escolhe pelo relógio — e como o
  desenvolvimento acontece à noite, o tema claro nunca era exercitado. Metade da
  interface estava fora de teste sem ninguém ter decidido isso. Hoje o roteiro
  aceita `--tema` e os dois são obrigatórios.
- **Ferramenta mal chamada não é ferramenta rigorosa, é ferramenta inútil.** O
  `qmllint` sem `-I` reportou 569 avisos; com o import path certo eram 313,
  todos de uma causa que não é defeito; e os 2 que sobraram depois de desligar
  essa categoria eram defeito de verdade. O barulho escondeu o sinal.
- **Medir muda o diagnóstico.** O custo de projeção parecia ser latência de
  abertura, que é irrelevante; era latência de clique, que é cinco vezes maior e
  aparece no gesto mais importante do app.
- **O enquadramento de um número importa mais que o número.** `read_all` roda
  uma vez por abertura; `_recomputar` roda por evento. O mesmo milissegundo vale
  coisas muito diferentes nos dois lugares.
