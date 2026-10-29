"""Leitura das tabelas de um item: propostas, lances, mensagens do chat e eventos."""

import re
from dataclasses import dataclass
from decimal import Decimal

from . import normalizacao as norm

RE_FORNECEDOR = re.compile(r"^(" + norm.RE_DOCUMENTO.pattern + r") - (.*)$")
RE_LANCE = re.compile(r"^R\$\s*([\d.]+,\d+)\s*(\*)?$")
RE_VALOR_UNITARIO = re.compile(r"^R\$\s*[\d.]+,\d+ \(unitário\)$")
RE_VALOR_TOTAL = re.compile(r"^R\$\s*[\d.]+,\d+ \(total\)$")
# linhas que identificam o autor de uma mensagem do chat (antecedem a data/hora)
RE_RESPONSAVEL = re.compile(
    r"^(Sistema(\s+para o)?|participante|Pelo participante|Pelo pregoeiro|Pregoeiro.*|"
    r"Agente de contratação.*|" + norm.RE_DOCUMENTO.pattern + r")$"
)
NOTA_LANCES_EXCLUIDOS = "(lances com * foram excluídos)"
RE_SEM_LANCES = re.compile(r"^Nenhum lance foi registrado para o Item \d+\.?$")  # item sem disputa


@dataclass
class Proposta:
    documento: str
    nome: str
    valor_ofertado: Decimal | None
    situacao: str
    valor_proposta: Decimal | None
    valor_negociado: Decimal | None
    pagina: int


@dataclass
class Lance:
    data_hora: object  # datetime
    participante: str
    valor: Decimal
    excluido: bool
    pagina: int


@dataclass
class Registro:
    """Mensagem do chat ou evento: data/hora + texto com espaços normalizados."""
    data_hora: object
    texto: str
    pagina: int


def ler_propostas(secao):
    """Cada proposta começa em '<CNPJ/CPF> - <nome>'; o nome pode quebrar linha até 'Benefício Me/Epp'."""
    linhas = secao.linhas
    inicios = [i for i, l in enumerate(linhas) if RE_FORNECEDOR.match(l.texto)]
    propostas = []
    for pos, ini in enumerate(inicios):
        fim = inicios[pos + 1] if pos + 1 < len(inicios) else len(linhas)
        bloco = [l.texto for l in linhas[ini:fim]]
        m = RE_FORNECEDOR.match(bloco[0])
        i = next((j for j, t in enumerate(bloco) if t.startswith("Benefício Me/Epp:")), 1)
        nome = [m.group(2), *bloco[1:i]]

        # valor ofertado: primeiro par unitário/total do bloco; situação: linhas até o próximo rótulo
        valor_ofertado, situacao = None, []
        for j in range(i, len(bloco)):
            if RE_VALOR_UNITARIO.match(bloco[j]):
                valor_ofertado = norm.valor(bloco[j])
                k = j + 2 if j + 1 < len(bloco) and RE_VALOR_TOTAL.match(bloco[j + 1]) else j + 1
                while k < len(bloco) and not bloco[k].endswith(":"):
                    situacao.append(bloco[k])
                    k += 1
                break

        propostas.append(Proposta(
            documento=m.group(1),
            nome=norm.espacos(" ".join(nome)),
            valor_ofertado=valor_ofertado,
            situacao=norm.espacos(" ".join(situacao)).strip(" -"),
            valor_proposta=valor_apos_rotulo(bloco, "Valor proposta:"),
            valor_negociado=valor_apos_rotulo(bloco, "Valor negociado:"),
            pagina=linhas[ini].pagina,
        ))
    return propostas


def valor_apos_rotulo(bloco, rotulo):
    """Valor unitário logo após o rótulo; None quando ausente ou 'Não Realizado'."""
    if rotulo in bloco:
        i = bloco.index(rotulo)
        if i + 1 < len(bloco) and RE_VALOR_UNITARIO.match(bloco[i + 1]):
            return norm.valor(bloco[i + 1])
    return None


def ler_lances(secao):
    """Retorna (lances, linhas_nao_reconhecidas). Cada lance ocupa 3 linhas: data/hora, participante, valor."""
    textos = secao.linhas
    lances, sobras, i = [], [], 0
    while i < len(textos):
        dh = norm.data_hora(textos[i].texto)
        if dh and i + 2 < len(textos):
            m = RE_LANCE.match(textos[i + 2].texto)
            if m:
                lances.append(Lance(
                    data_hora=dh,
                    participante=textos[i + 1].texto,
                    valor=norm.valor("R$ " + m.group(1)),
                    excluido=bool(m.group(2)),
                    pagina=textos[i].pagina,
                ))
                i += 3
                continue
        if textos[i].texto != NOTA_LANCES_EXCLUIDOS and not RE_SEM_LANCES.match(textos[i].texto):
            sobras.append(textos[i].texto)
        i += 1
    return lances, sobras


def ler_registros(secao, com_responsavel):
    """Mensagens do chat (com_responsavel=True) ou eventos: texto entre uma data/hora e a próxima.

    No chat, as linhas de autor ('Sistema', 'Pelo participante', CNPJ...) que antecedem a próxima
    data/hora são removidas do texto da mensagem anterior.
    """
    registros, atual, corpo = [], None, []

    def fechar():
        if atual is None:
            return
        while com_responsavel and corpo and RE_RESPONSAVEL.match(corpo[-1]):
            corpo.pop()
        registros.append(Registro(atual[0], norm.juntar_quebras(" ".join(corpo)), atual[1]))

    for l in secao.linhas:
        dh = norm.data_hora(l.texto)
        if dh:
            fechar()
            atual, corpo = (dh, l.pagina), []
        else:
            corpo.append(l.texto)
    fechar()
    return registros
