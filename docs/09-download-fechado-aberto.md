# Download dos pregões Fechado-Aberto (2023-04 a 2026-10)

Guia para baixar, em qualquer máquina, os zips "Todos os relatórios e termos" das compras com modo de
disputa **Fechado-Aberto**. Usa os mesmos scripts do Aberto-Fechado (`baixar_manual.py --auto` e o
userscript), com a opção `--modo fechado-aberto`, que separa as pastas do registro e dos PDFs.

## 1. A amostra

Mesma seleção da amostra Aberto-Fechado (`registro.SELECAO`), trocando só o modo de disputa. Consultado em
`dados/pncp.db` em 20/11/2026:

- compra com `modo_disputa = 'Fechado-Aberto'`;
- item principal (`registro_principal = 1`) **homologado**, e o mês é o da `data_resultado` do item;
- com `id_compra`, ou seja, compra do Compras.gov.br (`fonte = 'dados_abertos'`), a única que abre na página
  do zip.

| | Compras |
|---|---:|
| Fechado-Aberto no `pncp.db` (todas) | 11.518 |
| com item homologado | 6.328 |
| com resultado homologado de 2023-04 a 2026-10 | 6.267 |
| **dessas, com `id_compra` (a amostra a baixar)** | **1.479** |
| Pregão Eletrônico | 1.415 |
| Pregão Presencial (registrado no Compras.gov.br) | 64 |
| fora da amostra: outras plataformas (`fonte = 'pncp'`, sem `id_compra`) | 4.788 (3.166 eletrônicos, 1.622 presenciais) |

São **1.479 compras distintas** e **24.749 itens homologados**. Como a lista é por mês do resultado, 75
compras aparecem em mais de um mês (1.576 compra-mês). O script baixa cada uma uma vez só: uma compra que
fica completa num mês é pulada nos outros. Os pregões presenciais entram porque a seleção do Aberto-Fechado
não filtra a modalidade. Para separá-los na análise, use `compras.modalidade_nome`.

Compras por mês do resultado (compra-mês). 2023-04 não tem nenhuma:

| Ano | Jan | Fev | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | | | | 0 | 1 | 14 | 13 | 29 | 16 | 27 | 19 | 21 | 140 |
| 2024 | 12 | 21 | 15 | 65 | 113 | 72 | 54 | 46 | 72 | 38 | 50 | 74 | 632 |
| 2025 | 36 | 62 | 49 | 37 | 63 | 58 | 61 | 38 | 43 | 32 | 32 | 30 | 541 |
| 2026 | 25 | 22 | 34 | 17 | 26 | 52 | 26 | 26 | 20 | 15 | | | 263 |

A lista fica versionada em `registro/compras_fechado-aberto/<AAAA-MM>.csv`, então quem não tem o
`pncp.db` (16 GB) recebe a lista com o `git pull`. Para regerar a lista (só quem tem o banco):

```powershell
# o banco precisa estar em dados/pncp.db, ou aponte PNCP_DADOS para a pasta dele
.\.venv\Scripts\python.exe registro.py compras --modo fechado-aberto
git add registro/compras_fechado-aberto/
```

## 2. Onde as coisas ficam

| O quê | Aberto-Fechado (padrão) | Fechado-Aberto (`--modo fechado-aberto`) |
|---|---|---|
| Lista de compras (git) | `registro/compras/<mês>.csv` | `registro/compras_fechado-aberto/<mês>.csv` |
| Registro do que foi tentado (git) | `registro/aberto-fechado_<mês>/<usuario>_manual.csv` | `registro/fechado-aberto_<mês>/<usuario>_manual.csv` |
| PDFs (fora do git) | `dados/filtrados/aberto-fechado_<mês>/relatorios/<compra>/` | `dados/filtrados/fechado-aberto_<mês>/relatorios/<compra>/` |

Os dois modos não se misturam: cada um só lê o próprio registro.

## 3. Preparar a máquina (uma vez)

Feito na máquina? Pule para a seção 4. Senão, siga o [README](../README.md) ("Uma vez, na máquina nova"):

```powershell
git clone https://github.com/ejlunelli-ship-it/PNCP-Automation.git
cd PNCP-Automation
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
git config user.name "Nome da Pessoa"     # vira o nome do arquivo da pessoa em registro/
```

Em cada navegador que for usar (Chrome, Edge e/ou Firefox):

1. Instale a extensão **Tampermonkey**. No Chrome, ative também "Permitir scripts de usuário" (ou o modo de
   desenvolvedor) na página da extensão.
2. Crie um script novo com o conteúdo de `navegador/compras_auto.user.js` (versão 1.3 ou mais nova). Deixe
   **uma só** versão ativa: duas versões juntas abrem e fecham o menu, e a compra sai como "sem botão".
3. Desligue a pergunta de onde salvar cada arquivo. No Chrome e no Edge, em Configurações > Downloads. No
   Firefox, em Configurações > Geral > Arquivos e aplicativos. Todos têm de salvar na pasta **Downloads** do
   usuário.
4. Entre no Compras.gov.br uma vez nesse navegador, para ver se a página da compra abre.

Detalhes em [navegador/README.md](../navegador/README.md) e em [07 §5.3](07-metodologia-de-extracao.md).

## 4. Dividir o trabalho

Cada compra cai sempre na mesma parte (`--parte k/n`, pelo SHA-1 do `numeroControlePNCP`). Defina `n` como o
**total de processos em todas as máquinas**: um processo por navegador. Cada processo fica com um `k`
diferente.

| Situação | Máquina 1 | Máquina 2 |
|---|---|---|
| 1 máquina, 3 navegadores | Chrome `1/3`, Edge `2/3`, Firefox `3/3` | não participa |
| 2 máquinas, 3 navegadores cada | Chrome `1/6`, Edge `2/6`, Firefox `3/6` | Chrome `4/6`, Edge `5/6`, Firefox `6/6` |
| 2 máquinas, 1 navegador cada | `1/2` | `2/2` |

Com 3 partes, cada uma tem cerca de 490 compras (505, 481 e 493). Ao mudar `n`, pare todos os processos e
relance todos juntos, senão duas partes abrem a mesma compra. Pouca memória (8 GB): use no máximo dois
navegadores.

## 5. Baixar

Em toda sessão, antes de começar:

```powershell
git pull
```

Um terminal por navegador (exemplo: máquina 1 de 2, com três navegadores):

```powershell
.\.venv\Scripts\python.exe baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04 --parte 1/6 --navegador chrome
.\.venv\Scripts\python.exe baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04 --parte 2/6 --navegador edge
.\.venv\Scripts\python.exe baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04 --parte 3/6 --navegador firefox
```

- A primeira linha do terminal tem de ser `Modo de disputa: Fechado-Aberto`. Se não for, faltou o `--modo`.
- Vai do mês mais recente (`--de`) ao mais antigo (`--ate`). Interrompido (tecla `s`, queda, falta de
  memória), basta rodar o **mesmo comando**: o que já está no registro é pulado.
- O hCaptcha não é contornado. Se a aba pedir um desafio (título `[PNCP auto] resolva o captcha`), resolva
  ali. `--max-falhas 0` desliga a pausa depois de falhas seguidas. Sem ele, o padrão de 3 pausa e pergunta
  se continua.
- Sem o userscript, rode sem `--auto` e clique você mesmo em Downloads > "Todos os relatórios e termos".
  Durante a espera, `p` pula a compra e `s` encerra.

Quando todos os processos terminarem a amostra inteira, repita as falhas temporárias num navegador livre,
com a mesma parte:

```powershell
.\.venv\Scripts\python.exe baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04 --parte 1/6 --navegador chrome --repetir --motivo "zip não recebido"
.\.venv\Scripts\python.exe baixar_manual.py --modo fechado-aberto --auto --intervalo 0 --max-falhas 0 --de 2026-10 --ate 2023-04 --parte 1/6 --navegador chrome --repetir --motivo "sem botão de downloads no site"
```

"Zip sem termos", "sem a opção no site", "compra não encontrada" e "acesso não autorizado" são respostas do
site. Não adianta repetir essas.

## 6. Salvar no git (no fim de cada sessão)

Só o registro vai para o git, nunca os PDFs:

```powershell
git add registro/fechado-aberto_*
git commit -m "Downloads manuais (auto) Fechado-Aberto: <meses>, parte k/n"
git pull --rebase
git push
```

Não há conflito de merge: cada pessoa só escreve no próprio arquivo `<usuario>_manual.csv`. Os PDFs ficam em
`dados/filtrados/fechado-aberto_<mês>/relatorios/` na máquina de quem baixou. Para juntar tudo numa máquina,
copie essas pastas. O `sha256` de cada linha do registro serve para conferir os arquivos.

## 7. Conferir o andamento

```powershell
# compras completas por mês, somando todos os usuários
.\.venv\Scripts\python.exe -c "import registro, collections; registro.usar_modo('fechado-aberto'); l=registro.ler(); c=collections.Counter(x['mes'] for x in l if x['situacao']=='completo'); print(sorted(c.items()), sum(c.values()))"
```

Compare com a tabela da seção 1: 1.479 compras distintas. Uma compra em mais de um mês conta só no mês em que
foi baixada.

## 8. Depois do download

- **Extração:** o parser (`extrator_homologacao`) foi feito e testado com termos de pregões
  **Aberto-Fechado**. No Fechado-Aberto a ordem das etapas é invertida: primeiro a fechada (propostas
  sigilosas), depois a aberta, só com os melhores classificados. Antes de extrair a amostra inteira, teste
  numa amostra e confira as colunas de etapa. Ver [05](05-decisoes-e-pendencias.md), pendência 16.
- Extraia num banco próprio (ex.: `dados/extracao/fechado-aberto_<meses>.db`), separado das bases do
  Aberto-Fechado.
