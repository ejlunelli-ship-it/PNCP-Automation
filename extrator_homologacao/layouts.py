"""Layouts do termo de homologação/julgamento do Compras.gov.br.

ATUAL: PDFs gerados a partir de ~fev/2025. É o layout descrito em docs/04 §4.1.

ANTIGO: PDFs gerados até ~fev/2025 (ex.: compras de 2023 e as de 2024 homologadas até então). As
seções e os rótulos são os mesmos, mas:

1. a ordem interna do PDF não é a de leitura: no bloco do item, os valores vêm antes dos rótulos e o
   título "Item N - ..." vem no fim da página; a continuação de uma tabela (ex.: o chat do item) vem
   depois da tabela seguinte (os eventos). O texto é refeito na ordem visual da página
   (`texto.paginas_em_ordem_visual`);
2. data/hora sem "às" no chat, nos eventos e nos lances do item ("28/07/2023 11:06:42");
3. valores sem "(unitário)"/"(total)": "Valor estimado:" "R$ 5,5100", "melhor lance: R$ 3,5800";
4. propostas com "Porte MeEpp/Equiparada:" no lugar de "Benefício Me/Epp:";
5. título "Lances do Item  N", com dois espaços;
6. no termo de homologação, o item não traz o critério de julgamento (só a compra, em geral
   "Menor Preço / Maior Desconto"): ver `campos.inferir_criterio`;
7. parágrafo de situação "Adjucado e Homologado por ..." (grafia do sistema).
"""

import re

from .texto import Linha

ATUAL, ANTIGO = "atual", "antigo"

RE_DATA_HORA_SEM_AS = re.compile(r"^(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2})$")
# últimas linhas do cabeçalho das tabelas de eventos ("Data/Hora", "Descrição") e de lances
# ("Data/hora", "Participante", "Lance"): a linha seguinte é a data/hora do primeiro registro
FIM_CABECALHO_TABELA = ("Descrição", "Lance")
MARCADOR_PROPOSTA_ANTIGO = "Porte MeEpp/Equiparada:"


def detectar(paginas):
    """Layout do relatório a partir do texto extraído na ordem interna do PDF.

    ANTIGO quando uma tabela de eventos ou de lances começa com data/hora sem "às" (no layout atual
    toda data/hora dessas tabelas tem "às") ou quando uma proposta traz "Porte MeEpp/Equiparada:".
    """
    anterior = None
    for pagina in paginas:
        for bruta in pagina.split("\n"):
            texto = bruta.strip()
            if not texto:
                continue
            if texto.startswith(MARCADOR_PROPOSTA_ANTIGO):
                return ANTIGO
            if anterior in FIM_CABECALHO_TABELA and RE_DATA_HORA_SEM_AS.match(texto):
                return ANTIGO
            anterior = texto
    return ATUAL


def normalizar(linhas):
    """Linhas do layout antigo na forma do atual: data/hora com "às" e espaços simples
    ("Lances do Item  72" -> "Lances do Item 72")."""
    saida = []
    for linha in linhas:
        texto = re.sub(r"\s+", " ", linha.texto).strip()
        m = RE_DATA_HORA_SEM_AS.match(texto)
        if m:
            texto = f"{m.group(1)} às {m.group(2)}"
        saida.append(Linha(linha.pagina, texto))
    return saida
