"""Extração dos campos de negócio a partir das seções já identificadas."""

import re
from dataclasses import dataclass, field

from . import normalizacao as norm
from .etapas import ABERTA, DESEMPATE, FECHADA

# --------------------------------------------------------------------------- cabeçalho da compra

RE_UASG = re.compile(r"^UASG (\d+)\b")
# linha da modalidade + número, ex.: "PREGÃO 96005/2026", "CONCORRÊNCIA 90001/2026"
RE_COMPRA = re.compile(r"^(?P<modalidade>[A-ZÀ-Ú][A-ZÀ-Ú ]*?) (?P<numero>\d[\d./-]*)$")


def apos_rotulo(textos, rotulo):
    """Texto da linha seguinte ao rótulo (ex.: 'Modo de disputa:' -> 'Aberto/Fechado')."""
    if rotulo in textos:
        i = textos.index(rotulo)
        if i + 1 < len(textos):
            return textos[i + 1]
    return None


def campos_cabecalho(secao):
    textos = secao.textos
    uasg = next((m.group(1) for t in textos if (m := RE_UASG.match(t))), None)
    compra = next((m for t in textos if (m := RE_COMPRA.match(t)) and not t.startswith("UASG")), None)
    modalidade = compra.group("modalidade") if compra else None
    numero = compra.group("numero") if compra else None
    return {
        "uasg": uasg,
        "modalidade_compra": modalidade,
        "numero_compra": numero,
        "pregao": numero if modalidade == "PREGÃO" else None,
        "modo_disputa": apos_rotulo(textos, "Modo de disputa:"),
    }


# --------------------------------------------------------------------------- bloco do item

def descricao_item(secao):
    """Título ('Item N - ...') e descrição até 'Quantidade:', com quebras de linha removidas."""
    textos = secao.textos
    fim = textos.index("Quantidade:") if "Quantidade:" in textos else len(textos)
    if not textos:
        return None
    primeira = re.sub(r"^Item \d+ - ", "", textos[0])
    return norm.espacos(" ".join([primeira, *textos[1:fim]])) or None


def valor_estimado(secao):
    """Retorna (unitario, total, texto_original). Valores None se o relatório não os informar."""
    textos = secao.textos
    if "Valor estimado:" not in textos:
        return None, None, None
    i = textos.index("Valor estimado:")
    unitario = total = None
    originais = []
    for t in textos[i + 1:i + 3]:
        if t.endswith("(unitário)"):
            unitario = norm.valor(t)
        elif t.endswith("(total)"):
            total = norm.valor(t)
        else:
            break
        originais.append(t)
    if not originais and i + 1 < len(textos):
        originais.append(textos[i + 1])  # ex.: "Sigiloso"
    return unitario, total, " / ".join(originais)


RE_SITUACAO_RESPONSAVEL = re.compile(r"^(?P<acao>[A-ZÀ-Ú][^:]*?) por (?:CPF|CNPJ) \S+ - ")
RE_ACEITO = re.compile(
    r" para (?P<fornecedor>.+?), (?:CNPJ|CPF) (?P<documento>" + norm.RE_DOCUMENTO.pattern + r")"
    r", melhor lance: (?P<melhor>R\$\s*[\d.]+,\d+) \(unitário\)"
    r"(?:.*?, valor negociado: (?P<negociado>R\$\s*[\d.]+,\d+) \(unitário\))?"
)


@dataclass
class SituacaoItem:
    situacao: str | None          # campo "Situação:" do item, ex.: "Adjudicado e Homologado"
    criterio: str | None          # critério de julgamento do item, ex.: "Menor Preço"
    acao: str | None = None       # ex.: "Aceito e Habilitado", "Adjudicado e Homologado", "Fracassado"
    texto: str | None = None      # parágrafo completo, para auditoria
    fornecedor: str | None = None
    documento: str | None = None
    melhor_lance: object = None
    valor_negociado: object = None
    pagina: int | None = None


def situacao_item(secao):
    """Lê 'Situação:', o critério do item e o parágrafo '<ação> por CPF ... para <fornecedor>, CNPJ ...'."""
    textos = secao.textos
    resultado = SituacaoItem(
        situacao=apos_rotulo(textos, "Situação:"),
        criterio=apos_rotulo(textos, "Critério de julgamento:"),
    )
    for i, linha in enumerate(secao.linhas):
        m = RE_SITUACAO_RESPONSAVEL.match(linha.texto)
        if not m:
            continue
        paragrafo = norm.juntar_quebras(" ".join(textos[i:]))
        resultado.acao = m.group("acao")
        resultado.texto = paragrafo
        resultado.pagina = linha.pagina
        a = RE_ACEITO.search(paragrafo)
        if a:
            resultado.fornecedor = a.group("fornecedor").strip()
            resultado.documento = a.group("documento")
            resultado.melhor_lance = norm.valor(a.group("melhor"))
            resultado.valor_negociado = norm.valor(a.group("negociado"))
        break
    return resultado


# --------------------------------------------------------------------------- fornecedores

def quantidade_fornecedores(propostas, lances, deserto=False):
    """Fornecedores distintos (por CNPJ/CPF) com proposta no item. Retorna (quantidade, problemas).

    Item deserto não recebeu propostas: a quantidade é 0, não um problema de leitura.
    """
    problemas = []
    docs = {norm.digitos(p.documento) for p in propostas}
    sem_proposta = {norm.digitos(l.participante) for l in lances} - docs
    if sem_proposta:
        problemas.append(f"{len(sem_proposta)} participante(s) com lance sem proposta listada no item")
    if not docs:
        if deserto:
            return 0, problemas
        problemas.append("nenhuma proposta identificada no item")
        return None, problemas
    return len(docs), problemas


# --------------------------------------------------------------------------- lances por etapa

@dataclass
class ResumoLances:
    menor: dict = field(default_factory=dict)   # etapa -> Decimal | None
    melhor: dict = field(default_factory=dict)  # etapa -> Decimal | None
    excluidos: int = 0
    nao_classificados: int = 0


def resumir_lances(classificados, criterio):
    """classificados: lista de (lance, etapa). Lances marcados com '*' (excluídos) são ignorados.

    'menor' é o menor valor registrado; 'melhor' é o mais vantajoso segundo o critério do item
    (menor valor para Menor Preço, maior para Maior Desconto) e fica None se o critério for desconhecido.
    """
    resumo = ResumoLances()
    criterio = (criterio or "").lower()
    for etapa in (ABERTA, FECHADA, DESEMPATE):
        valores = [l.valor for l, e in classificados if e == etapa and not l.excluido]
        resumo.menor[etapa] = min(valores) if valores else None
        if not valores:
            resumo.melhor[etapa] = None
        elif "menor preço" in criterio:
            resumo.melhor[etapa] = min(valores)
        elif "maior desconto" in criterio:
            resumo.melhor[etapa] = max(valores)
        else:
            resumo.melhor[etapa] = None
    resumo.excluidos = sum(1 for l, _ in classificados if l.excluido)
    resumo.nao_classificados = sum(1 for l, e in classificados if e is None and not l.excluido)
    return resumo


# --------------------------------------------------------------------------- lance aceito

ACEITO, ADJUDICADO, HOMOLOGADO = "ACEITO", "ADJUDICADO", "HOMOLOGADO"
DESCLASSIFICADO, FRACASSADO = "DESCLASSIFICADO", "FRACASSADO"
NAO_IDENTIFICADO, REVISAR = "NÃO IDENTIFICADO", "REVISAR"
EM_ANDAMENTO, DESERTO, CANCELADO = "EM ANDAMENTO", "DESERTO", "CANCELADO"
REVOGADO, ANULADO, SUSPENSO = "REVOGADO", "ANULADO", "SUSPENSO"

# (trecho da "Situação:" do item, resultado), na ordem de teste: o primeiro que bater vence
RESULTADOS = [
    ("fracassad", FRACASSADO), ("desert", DESERTO), ("revogad", REVOGADO), ("anulad", ANULADO),
    ("cancelad", CANCELADO), ("suspens", SUSPENSO), ("homologad", HOMOLOGADO),
    ("aguardando adjudica", EM_ANDAMENTO), ("adjudicad", ADJUDICADO),
    ("recurso", EM_ANDAMENTO), ("aceit", EM_ANDAMENTO), ("habilita", EM_ANDAMENTO), ("julgamento", EM_ANDAMENTO),
]


SEM_ACEITE = {FRACASSADO, DESERTO, REVOGADO, ANULADO, CANCELADO}


def resultado_item(situacao):
    """Resultado do item a partir da "Situação:" ("Fracassado e Homologado" -> FRACASSADO,
    "Adjudicado e Homologado" -> HOMOLOGADO, "Aguardando adjudicação" -> EM ANDAMENTO)."""
    texto = (situacao or "").lower()  # os trechos param antes de acentos ("adjudica|ção")
    for trecho, resultado in RESULTADOS:
        if trecho in texto:
            return resultado
    return NAO_IDENTIFICADO

RE_EVENTO_PROPOSTA = re.compile(
    r"^Fornecedor (?P<fornecedor>.+?), (?:CNPJ|CPF) (?P<documento>" + norm.RE_DOCUMENTO.pattern + r") "
    r"teve a proposta (?P<acao>aceita|adjudicada|desclassificada|recusada), melhor lance: (?P<valor>R\$\s*[\d.]+,\d+)"
)
RE_EVENTO_INABILITADO = re.compile(
    r"^Fornecedor (?P<fornecedor>.+?), (?:CNPJ|CPF) (?P<documento>" + norm.RE_DOCUMENTO.pattern + r") foi inabilitado"
)


@dataclass
class LanceAceito:
    valor: object = None
    fornecedor: str | None = None
    documento: str | None = None
    situacao: str = NAO_IDENTIFICADO
    valor_negociado: object = None
    fonte: str | None = None
    problemas: list = field(default_factory=list)  # motivos para REVISAR
    avisos: list = field(default_factory=list)


def classificar_acao(acao):
    acao = (acao or "").lower()
    if acao.startswith("fracassad"):
        return FRACASSADO
    if "homologad" in acao and ("aceit" in acao or "adjudicad" in acao):
        return HOMOLOGADO
    if "adjudicad" in acao:
        return ADJUDICADO
    if "aceit" in acao:
        return ACEITO
    return None


def lance_aceito(situacao, propostas, eventos, pagina_eventos=""):
    """Valor e fornecedor efetivamente aceitos para o item, com base na situação final do item.

    Fonte principal: o parágrafo de situação do item ("Aceito e Habilitado / Adjudicado e Homologado
    por ... para <fornecedor>, CNPJ ..., melhor lance: ...[, valor negociado: ...]"). A tabela de
    propostas e os eventos do item são usados para confirmar; qualquer contradição leva a REVISAR.
    Mensagens do chat não são usadas como evidência de aceitação.
    """
    r = LanceAceito()
    tipo = classificar_acao(situacao.acao)
    fonte = f"situação do item (p.{situacao.pagina})" if situacao.pagina else "situação do item"

    # fracassado, deserto, revogado etc.: o item terminou sem proposta aceita
    resultado = resultado_item(situacao.situacao)
    if tipo == FRACASSADO or resultado in SEM_ACEITE:
        r.situacao = FRACASSADO if tipo == FRACASSADO else resultado
        r.fonte = fonte
        r.avisos.append(f"item '{situacao.situacao}': nenhuma proposta aceita")
        return r

    if tipo is None:
        r.situacao = NAO_IDENTIFICADO
        motivo = (f"ação '{situacao.acao}' não indica aceitação" if situacao.acao
                  else f"situação do item '{situacao.situacao}' sem registro de proposta aceita")
        r.problemas.append(f"lance aceito não identificado: {motivo}")
        return r

    if not situacao.documento or situacao.melhor_lance is None:
        r.situacao = REVISAR
        r.problemas.append(f"situação '{situacao.acao}' sem fornecedor/valor reconhecíveis: {situacao.texto!r}")
        return r

    r.fornecedor, r.documento, r.fonte = situacao.fornecedor, situacao.documento, fonte
    r.valor_negociado = situacao.valor_negociado
    candidato = situacao.valor_negociado if situacao.valor_negociado is not None else situacao.melhor_lance

    # confirmação na tabela de propostas
    doc = norm.digitos(situacao.documento)
    proposta = next((p for p in propostas if norm.digitos(p.documento) == doc), None)
    if proposta is None:
        r.problemas.append(f"fornecedor aceito {situacao.documento} não consta na tabela de propostas")
    else:
        if "desclassificad" in proposta.situacao.lower():
            r.situacao = DESCLASSIFICADO
            r.problemas.append(f"situação do item aponta {situacao.documento} como aceito, mas a proposta consta como '{proposta.situacao}'")
            return r
        if proposta.valor_negociado != situacao.valor_negociado:
            r.problemas.append(
                f"valor negociado diverge: situação do item {situacao.valor_negociado}, "
                f"tabela de propostas {proposta.valor_negociado}"
            )

    # confirmação nos eventos do item (último evento de aceitação/adjudicação)
    decisoes = [(e, m) for e in eventos if (m := RE_EVENTO_PROPOSTA.search(e.texto)) and m.group("acao") in ("aceita", "adjudicada")]
    if decisoes:
        evento, m = decisoes[-1]
        if norm.digitos(m.group("documento")) != doc:
            r.problemas.append(
                f"último evento de aceitação/adjudicação (p.{evento.pagina}) é de {m.group('documento')}, "
                f"diferente do fornecedor da situação do item {situacao.documento}"
            )
        elif norm.valor(m.group("valor")) not in (situacao.melhor_lance, situacao.valor_negociado):
            r.problemas.append(
                f"valor do evento de {m.group('acao')} (p.{evento.pagina}) {norm.valor(m.group('valor'))} "
                f"diverge da situação do item {situacao.melhor_lance}"
            )
        else:
            r.fonte += f" + evento '{m.group('acao')}' (p.{evento.pagina})"
        inabilitado_depois = [
            e for e in eventos
            if e.data_hora > evento.data_hora and (mi := RE_EVENTO_INABILITADO.search(e.texto)) and norm.digitos(mi.group("documento")) == doc
        ]
        if inabilitado_depois:
            r.problemas.append(f"fornecedor {situacao.documento} inabilitado após a aceitação (p.{inabilitado_depois[-1].pagina})")

    if r.problemas:
        r.situacao = REVISAR
        return r
    r.valor = candidato
    r.situacao = tipo
    return r
