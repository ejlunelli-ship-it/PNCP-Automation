"""Escolha de qual relatório usar por item (só biblioteca padrão: também é usado pelo relatorios.py).

Por item da compra: o termo de homologação, que traz a situação final; sem ele, o termo de
julgamento da última sessão (-sN-), pois uma sessão anterior pode mostrar um lance aceito que
depois fracassou. Diligências e outros arquivos não entram.
"""

import re
from pathlib import PurePath

HOMOLOGACAO = re.compile(r"^relatorio-termo-homologacao-(?P<compra>\d+)-item-(?P<item>\d+)\.pdf$", re.I)
JULGAMENTO = re.compile(r"^relatorio-julg-hab-(?P<compra>\d+)-s(?P<sessao>\d+)-item-(?P<item>\d+)\.pdf$", re.I)


def id_compra(caminho):
    """idCompra do Compras.gov.br no nome do relatório (ex.: 98205105911072026), ou None."""
    nome = PurePath(caminho).name
    m = HOMOLOGACAO.match(nome) or JULGAMENTO.match(nome)
    return m["compra"] if m else None


def selecionar(caminhos):
    """Subconjunto de `caminhos` (str ou Path, em qualquer pasta) com um relatório por item, na ordem recebida."""
    escolhido = {}  # (compra, item) -> (prioridade, caminho); maior prioridade vence
    for c in caminhos:
        nome = PurePath(c).name
        if m := HOMOLOGACAO.match(nome):
            prioridade = (1, 0)
        elif m := JULGAMENTO.match(nome):
            prioridade = (0, int(m["sessao"]))
        else:
            continue
        chave = (m["compra"], int(m["item"]))
        if chave not in escolhido or prioridade > escolhido[chave][0]:
            escolhido[chave] = (prioridade, c)
    manter = {c for _, c in escolhido.values()}
    return [c for c in caminhos if c in manter]
