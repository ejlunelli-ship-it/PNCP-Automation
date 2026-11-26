# Download dos pregões Aberto (todos os desfechos, 2022-11 a 2026-10)

Guia para baixar, em qualquer máquina, os zips "Todos os relatórios e termos" das compras com modo de
disputa **Aberto**. Usa os mesmos scripts do Aberto-Fechado e do Fechado-Aberto (`baixar_manual.py --auto`
e o userscript), com `--modo aberto`, que separa as pastas do registro e dos PDFs. Passo a passo de
instalação do ambiente e do userscript: README da raiz e [navegador/README.md](../navegador/README.md).

## 1. A amostra (decidida em 2026-11-26)

Diferente do AF e do FA, que foram baixados só com itens homologados:

- **Todos os desfechos:** compra com ao menos um item já decidido (Homologado, Fracassado, Deserto ou
  Anulado/Revogado/Cancelado). Ficam de fora as compras com todos os itens "Em andamento" (17.880), que ainda
  não têm termo; se forem incluídas depois, basta tirar o `EXISTS` de `registro.SELECAO_TODOS`.
- **Mês = data de publicação da compra no PNCP** (e não a `data_resultado`, que só existe para item com
  resultado). Por isso a lista começa em 2022-11.
- **Só Pregão Eletrônico** (sem presenciais) e só compra com `id_compra`, ou seja, do Compras.gov.br
  (`fonte = 'dados_abertos'`), a única que abre na página do zip.
- Consultado em `dados/pncp.db` em 26/11/2026: **184.177 compras** em 48 meses (2022-11 a 2026-10), de
  202.057 compras Aberto eletrônicas do Compras.gov.br. Itens principais dessas compras por situação:
  Homologado 2.800.577, Fracassado 365.506, Em andamento 362.326, Anulado/Revogado/Cancelado 187.947,
  Deserto 114.471. Cerca de 3 milhões de PDFs, um por item: **espaço em disco e tempo** (14 a 20 compras por
  minuto, de 135 a 195 horas) pesam; acompanhe o disco.
- O seletor de PDF é o mesmo (`selecao.py`): por item, o termo de homologação ou, sem ele, o termo de
  julgamento da última sessão. Não foi medido quantos itens não homologados têm esse termo; compra sem
  nenhum termo fica como "zip sem termos".

A lista das compras está em `registro/compras_aberto/<AAAA-MM>.csv` (versionada, uma por mês): quem não tem o
`pncp.db` usa essa lista. Para regerá-la: `python registro.py compras --modo aberto`.

## 2. Onde ficam os arquivos

| O quê | Onde |
|---|---|
| Lista de compras | `registro/compras_aberto/<mês>.csv` |
| Registro do que foi baixado | `registro/aberto_<mês>/<usuario>_manual.csv` |
| PDFs | `dados/filtrados/aberto_<mês>/relatorios/` (fora do git) |

## 3. Como baixar

Em ordem crescente (do mês mais antigo ao mais recente), um navegador por janela, dividindo as compras com
`--parte k/n`:

```powershell
git pull
.\.venv\Scripts\python.exe baixar_manual.py --modo aberto --crescente --de 2022-11 --ate 2026-10 --auto --intervalo 0 --max-falhas 0 --navegador firefox --parte 1/3
# idem com --navegador chrome --parte 2/3 e --navegador edge --parte 3/3
git add registro/
git commit -m "Downloads manuais (auto) Aberto"
git push
```

Com duas máquinas, combinem antes quem pega cada faixa de meses (`--de`/`--ate`) ou usem `--parte k/n` com
`n` igual ao total de janelas das duas máquinas (ex.: 6, três em cada). O que já foi resolvido, por qualquer
usuário, é pulado depois do `git pull`. No fim, repetir só `--repetir --motivo "zip não recebido"`.
