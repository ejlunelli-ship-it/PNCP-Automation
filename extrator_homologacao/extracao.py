"""Extração de um relatório: do texto das páginas até o dicionário de campos de uma linha."""

import re
from dataclasses import dataclass, field

from . import campos, etapas, tabelas
from .secoes import segmentar
from .texto import linhas_limpas

TIPOS_SUPORTADOS = ("TERMO DE HOMOLOGAÇÃO", "TERMO DE JULGAMENTO")
RE_ITEM_ARQUIVO = re.compile(r"item-(\d+)\.pdf$", re.I)


class RelatorioNaoSuportado(Exception):
    pass


@dataclass
class Resultado:
    dados: dict = field(default_factory=dict)
    problemas: list = field(default_factory=list)  # tornam o relatório REVISAR
    avisos: list = field(default_factory=list)     # registrados, sem exigir revisão
    fontes: list = field(default_factory=list)     # página/seção de cada campo


def escolher_item(documento, nome_arquivo):
    """Item representado pelo relatório: o único item do PDF ou o indicado no nome do arquivo."""
    m = RE_ITEM_ARQUIVO.search(nome_arquivo)
    numero_arquivo = int(m.group(1)) if m else None
    itens = documento.itens
    if not itens:
        return None, "nenhum bloco de item encontrado no relatório"
    if numero_arquivo is not None:
        if numero_arquivo in itens:
            return itens[numero_arquivo], None
        return None, f"arquivo indica item {numero_arquivo}, mas o relatório traz os itens {sorted(itens)}"
    if len(itens) == 1:
        return next(iter(itens.values())), None
    return None, f"relatório com vários itens {sorted(itens)} e nenhum item indicado no nome do arquivo"


def extrair_documento(paginas, nome_arquivo):
    documento = segmentar(linhas_limpas(paginas))
    if documento.tipo not in TIPOS_SUPORTADOS:
        raise RelatorioNaoSuportado(f"tipo de relatório não suportado: {documento.tipo or 'não identificado'}")

    r = Resultado()
    r.dados["tipo_relatorio"] = documento.tipo
    r.dados.update(campos.campos_cabecalho(documento.cabecalho))
    r.fontes.append(f"uasg/pregao/modo_disputa: cabeçalho {documento.cabecalho.paginas}")

    bloco, problema = escolher_item(documento, nome_arquivo)
    if bloco is None:
        r.problemas.append(problema)
        return r
    extrair_item(bloco, r)
    return r


def extrair_item(bloco, r):
    d = r.dados
    d["item"] = bloco.numero
    d["descricao_item"] = campos.descricao_item(bloco.cabecalho)

    unitario, total, original = campos.valor_estimado(bloco.cabecalho)
    d["valor_estimado"], d["valor_estimado_total"] = unitario, total
    if unitario is None:
        r.avisos.append(f"valor estimado não informado explicitamente ({original or 'campo ausente'})")
    r.fontes.append(f"descricao_item/valor_estimado: Item {bloco.numero} {bloco.cabecalho.paginas}")

    situacao = campos.situacao_item(bloco.cabecalho)
    d["situacao_item"] = situacao.situacao
    d["criterio_julgamento_item"] = situacao.criterio

    propostas = tabelas.ler_propostas(bloco.propostas)
    lances, sobras = tabelas.ler_lances(bloco.lances)
    if sobras:
        r.problemas.append(f"{len(sobras)} linha(s) não reconhecida(s) na tabela de lances: {sobras[:3]}")

    d["quantidade_fornecedores"], probs = campos.quantidade_fornecedores(propostas, lances)
    r.problemas.extend(probs)
    r.fontes.append(f"quantidade_fornecedores: Propostas do Item {bloco.numero} {bloco.propostas.paginas}")

    eventos = tabelas.ler_registros(bloco.eventos, com_responsavel=False)
    extrair_lances(bloco, lances, eventos, situacao.criterio, d.get("modo_disputa"), r)

    aceito = campos.lance_aceito(situacao, propostas, eventos)
    d["lance_aceito"] = aceito.valor
    d["fornecedor_lance_aceito"] = aceito.fornecedor
    d["cnpj_fornecedor_lance_aceito"] = aceito.documento
    d["situacao_lance_aceito"] = aceito.situacao
    d["valor_negociado_aceito"] = aceito.valor_negociado
    r.problemas.extend(aceito.problemas)
    r.avisos.extend(aceito.avisos)
    if aceito.fonte:
        r.fontes.append(f"lance_aceito: {aceito.fonte}")


def extrair_lances(bloco, lances, eventos, criterio, modo, r):
    d = r.dados
    for campo in ("menor_lance_modo_aberto", "menor_lance_modo_fechado", "melhor_lance_modo_aberto",
                  "melhor_lance_modo_fechado", "menor_lance_desempate"):
        d[campo] = None
    d["lances_excluidos"] = sum(1 for l in lances if l.excluido)

    if not bloco.lances:
        r.avisos.append("item sem tabela de lances")
        return
    if not lances:
        r.avisos.append("tabela de lances sem lances")
        return

    chat = tabelas.ler_registros(bloco.chat, com_responsavel=True)
    marcos, probs = etapas.identificar_etapas(chat, eventos, bloco.numero)
    r.problemas.extend(probs)
    modo_norm = (modo or "").strip().lower()
    if modo_norm in ("aberto", "fechado"):
        # etapa única: todos os lances são dela, exceto os que caem numa janela de desempate
        unica = etapas.ABERTA if modo_norm == "aberto" else etapas.FECHADA
        desempates = [j for j in marcos.janelas if j.etapa == etapas.DESEMPATE]
        classificados = [(l, etapas.DESEMPATE if any(j.contem(l.data_hora) for j in desempates) else unica) for l in lances]
        resolvidos = 0
    elif modo_norm == "aberto/fechado":
        if not marcos.fechadas():
            r.problemas.append("não foi possível identificar a etapa fechada no chat nem nos eventos do item")
            return
        classificados, resolvidos = etapas.classificar_lances(lances, marcos)
    else:
        r.problemas.append(f"modo de disputa {modo!r} sem regra de separação de lances por etapa")
        return
    if resolvidos:
        r.avisos.append(f"{resolvidos} lance(s) no limite entre etapas atribuído(s) pela mensagem de encerramento da etapa")
    resumo = campos.resumir_lances(classificados, criterio)
    if resumo.nao_classificados:
        exemplos = [f"{l.data_hora:%d/%m %H:%M:%S} {l.valor}" for l, e in classificados if e is None and not l.excluido]
        r.problemas.append(f"{resumo.nao_classificados} lance(s) sem etapa determinável: {exemplos[:3]}")
        return
    r.problemas.extend(etapas.conferir_com_chat(classificados, marcos))

    d["menor_lance_modo_aberto"] = resumo.menor[etapas.ABERTA]
    d["menor_lance_modo_fechado"] = resumo.menor[etapas.FECHADA]
    d["menor_lance_desempate"] = resumo.menor[etapas.DESEMPATE]
    d["melhor_lance_modo_aberto"] = resumo.melhor[etapas.ABERTA]
    d["melhor_lance_modo_fechado"] = resumo.melhor[etapas.FECHADA]
    if modo_norm == "aberto/fechado" and resumo.menor[etapas.FECHADA] is None:
        r.avisos.append("nenhum lance registrado na etapa fechada")
    if resumo.excluidos:
        r.avisos.append(f"{resumo.excluidos} lance(s) marcados como excluídos (*) desconsiderados")
    if lances and resumo.melhor[etapas.ABERTA] is None and resumo.menor[etapas.ABERTA] is not None:
        r.problemas.append(f"critério de julgamento do item não reconhecido ({criterio!r}): melhor lance não definido")
    r.fontes.append(
        f"lances: Lances do Item {bloco.numero} {bloco.lances.paginas}; etapas: {marcos.origem}"
    )
