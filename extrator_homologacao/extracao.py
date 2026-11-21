"""Extração de um relatório: do texto das páginas até o dicionário de campos de uma linha."""

import re
from dataclasses import dataclass, field

from . import campos, etapas, layouts, tabelas
from . import normalizacao as norm
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


def extrair_documento(paginas, nome_arquivo, layout=layouts.ATUAL):
    """`paginas`: texto de cada página; no layout antigo, na ordem visual (ver `layouts`)."""
    linhas = linhas_limpas(paginas)
    if layout == layouts.ANTIGO:
        linhas = layouts.normalizar(linhas)
    documento = segmentar(linhas, antigo=layout == layouts.ANTIGO)
    documento.layout = layout
    if documento.tipo not in TIPOS_SUPORTADOS:
        raise RelatorioNaoSuportado(f"tipo de relatório não suportado: {documento.tipo or 'não identificado'}")

    r = Resultado()
    r.dados["tipo_relatorio"] = documento.tipo
    r.dados.update(campos.campos_cabecalho(documento.cabecalho))
    if layout == layouts.ANTIGO:
        r.fontes.append("layout antigo: texto na ordem visual da página")
    r.fontes.append(f"uasg/pregao/modo_disputa: cabeçalho {documento.cabecalho.paginas}")

    bloco, problema = escolher_item(documento, nome_arquivo)
    if bloco is None:
        r.problemas.append(problema)
        return r
    extrair_item(bloco, r, documento)
    return r


def extrair_item(bloco, r, documento):
    d = r.dados
    antigo = documento.layout == layouts.ANTIGO
    d["item"] = bloco.numero
    d["grupo"] = bloco.grupo
    d["descricao_item"] = campos.descricao_item(bloco.cabecalho, antigo)

    unitario, total, original = campos.valor_estimado(bloco.cabecalho, antigo)
    d["valor_estimado"], d["valor_estimado_total"] = unitario, total
    if unitario is None:
        r.avisos.append(f"valor estimado não informado explicitamente ({original or 'campo ausente'})")
    r.fontes.append(f"descricao_item/valor_estimado: Item {bloco.numero} {bloco.cabecalho.paginas}")
    if antigo and unitario is not None and total is None:
        # o layout antigo não imprime o total; no atual, total = unitário × quantidade
        quantidade = campos.quantidade_item(bloco.cabecalho)
        if quantidade is not None and quantidade > 0:
            d["valor_estimado_total"] = unitario * quantidade
            r.fontes.append("valor_estimado_total: valor estimado × quantidade (ausente no layout antigo)")

    situacao = campos.situacao_item(bloco.cabecalho, antigo)
    d["situacao_item"] = situacao.situacao
    d["resultado"] = campos.resultado_item(situacao.situacao)
    if d["resultado"] == campos.NAO_IDENTIFICADO:
        r.avisos.append(f"resultado do item não reconhecido na situação {situacao.situacao!r}")

    propostas = tabelas.ler_propostas(bloco.propostas, antigo)
    lances, sobras = tabelas.ler_lances(bloco.lances)
    if sobras:
        r.problemas.append(f"{len(sobras)} linha(s) não reconhecida(s) na tabela de lances: {sobras[:3]}")

    if situacao.criterio is None and antigo:
        # o termo de homologação antigo só traz o critério da compra (em geral "Menor Preço / Maior Desconto")
        situacao.criterio, regra = campos.inferir_criterio(
            campos.apos_rotulo(documento.cabecalho.textos, "Critério de julgamento:"),
            bloco.propostas.textos + bloco.lances.textos)
        if situacao.criterio is None:
            r.avisos.append(f"critério de julgamento do item ausente no relatório e {regra}")
        else:
            r.fontes.append(f"criterio_julgamento_item: ausente no item, inferido {regra}")
    d["criterio_julgamento_item"] = situacao.criterio

    d["quantidade_fornecedores"], probs, avs = campos.quantidade_fornecedores(
        propostas, lances, deserto=d["resultado"] == campos.DESERTO)
    r.problemas.extend(probs)
    r.avisos.extend(avs)
    r.fontes.append(f"quantidade_fornecedores: Propostas do Item {bloco.numero} {bloco.propostas.paginas}")
    desclassificados = campos.fornecedores_desclassificados(propostas)
    d["fornecedores_desclassificados"] = "; ".join(desclassificados) or None
    d["quantidade_desclassificados"] = len(desclassificados) if propostas else None

    eventos = tabelas.ler_registros(bloco.eventos, com_responsavel=False, antigo=antigo)
    extrair_lances(bloco, lances, propostas, eventos, situacao.criterio, d.get("modo_disputa"), r, documento)

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
    preencher_percentuais(bloco, r)


CAMPOS_COM_PERCENTUAL = ("melhor_lance_modo_aberto", "melhor_lance_modo_fechado", "melhor_lance_desempate",
                         "lance_aceito", "valor_negociado_aceito")


def preencher_percentuais(bloco, r):
    """Maior Desconto: percentual de cada valor gravado, lido do par "P% (R$ V)" do próprio item."""
    d = r.dados
    if "maior desconto" not in (d.get("criterio_julgamento_item") or "").lower():
        return
    secoes = (bloco.cabecalho, bloco.propostas, bloco.lances, bloco.chat, bloco.eventos)
    textos = [norm.juntar_quebras(" ".join(s.textos)) for s in secoes if s]
    mapa, avisos = campos.percentuais_do_item(textos, d.get("valor_estimado"))
    r.avisos.extend(avisos)
    for campo in CAMPOS_COM_PERCENTUAL:
        valor = d.get(campo)
        if valor is None:
            continue
        d[f"{campo}_percentual"] = mapa.get(valor)
        if valor not in mapa:
            r.avisos.append(f"{campo}: percentual não encontrado para R$ {valor}")
    r.fontes.append(f"percentuais: pares 'P% (R$ V)' do Item {bloco.numero}")


def itens_do_grupo(documento, rotulo):
    """(quantidade, lances, propostas) de cada item do grupo, para conferir os totais da etapa fechada."""
    antigo = documento.layout == layouts.ANTIGO
    return [(campos.quantidade_item(b.cabecalho), tabelas.ler_lances(b.lances)[0],
             tabelas.ler_propostas(b.propostas, antigo))
            for b in documento.itens.values() if b.grupo == rotulo]


CAMPOS_LIDERANCA = ("cnpj_melhor_lance_aberto", "melhor_lance_modo_aberto_outro_fornecedor",
                    "melhor_lance_modo_aberto_validos", "melhor_lance_modo_fechado_validos",
                    "lider_aberto_lance_fechado", "reinicios_etapa_fechada")


def preencher_fechada_das_propostas(d, propostas, criterio, r, avisar=True):
    """Fechado-Aberto: a etapa fechada é a proposta sigilosa de cada fornecedor ("Valor proposta").

    O melhor valor dela vai para `melhor_lance_modo_fechado`; sem os desclassificados, para
    `melhor_lance_modo_fechado_validos`. As propostas não convocadas para a etapa aberta saem como
    "desclassificada por não atender aos critérios de classificação do modo de disputa fechado/aberto",
    mas nunca são a melhor proposta, então não mudam o valor válido.
    """
    fora = {campos.chave_fornecedor(x) for x in campos.fornecedores_desclassificados(propostas)}
    d["melhor_lance_modo_fechado"] = campos.mais_vantajoso([p.valor_proposta for p in propostas], criterio)
    d["melhor_lance_modo_fechado_validos"] = campos.mais_vantajoso(
        [p.valor_proposta for p in propostas if campos.chave_fornecedor(p.documento) not in fora], criterio)
    if avisar:
        if d["melhor_lance_modo_fechado"] is None and propostas:  # sem proposta (deserto) não há etapa fechada
            r.problemas.append("Fechado-Aberto: nenhum valor de proposta (etapa fechada) identificado")
        r.fontes.append("melhor_lance_modo_fechado: Valor proposta (etapa fechada do Fechado-Aberto)")


def preencher_lideranca(d, propostas, abertos, fechados, criterio, com_fechada):
    """Líder da etapa aberta, melhor valor de outro fornecedor e melhores valores sem os desclassificados."""
    desclassificados = campos.fornecedores_desclassificados(propostas)
    lid = campos.lideranca_aberta(abertos, fechados, desclassificados, criterio, com_fechada)
    formatado = {campos.chave_fornecedor(p.documento): p.documento for p in propostas}
    d["cnpj_melhor_lance_aberto"] = (formatado.get(campos.chave_fornecedor(lid.documento), lid.documento)
                                     if lid.documento else None)
    d["melhor_lance_modo_aberto_outro_fornecedor"] = lid.outro_fornecedor
    d["melhor_lance_modo_aberto_validos"] = lid.aberto_validos
    d["melhor_lance_modo_fechado_validos"] = lid.fechado_validos
    d["lider_aberto_lance_fechado"] = lid.lider_lance_fechado


def extrair_lances(bloco, lances, propostas, eventos, criterio, modo, r, documento):
    d = r.dados
    for campo in ("melhor_lance_modo_aberto", "melhor_lance_modo_fechado", "melhor_lance_desempate") + CAMPOS_LIDERANCA:
        d[campo] = None
    d["lances_excluidos"] = sum(1 for l in lances if l.excluido)
    modo_norm = (modo or "").strip().lower()
    fechado_aberto = modo_norm == "fechado/aberto"
    # as propostas iniciais ("Valor proposta") abrem a etapa aberta e contam no melhor valor dela; no
    # Fechado-Aberto elas são a própria etapa fechada (lance único e sigiloso) e os convocados partem delas
    # na etapa aberta, então contam nas duas
    iniciais = [p.valor_proposta for p in propostas] if modo_norm in ("aberto", "aberto/fechado", "fechado/aberto") else []
    abertos_iniciais = ([(p.documento, p.valor_proposta, None) for p in propostas]
                        if modo_norm in ("aberto", "aberto/fechado", "fechado/aberto") else [])
    if fechado_aberto:
        preencher_fechada_das_propostas(d, propostas, criterio, r)

    if not bloco.lances or not lances:
        r.avisos.append("item sem tabela de lances" if not bloco.lances else "tabela de lances sem lances")
        d["melhor_lance_modo_aberto"] = campos.mais_vantajoso(iniciais, criterio)
        preencher_lideranca(d, propostas, abertos_iniciais, [], criterio, com_fechada=False)
        if fechado_aberto:
            preencher_fechada_das_propostas(d, propostas, criterio, r, avisar=False)
        return

    # em grupo, os marcos das etapas ficam no chat e nos eventos do grupo, com o rótulo "item G1"
    grupo = documento.grupos.get(bloco.grupo)
    origem = grupo or bloco
    antigo = documento.layout == layouts.ANTIGO
    chat = tabelas.ler_registros(origem.chat, com_responsavel=True, antigo=antigo)
    eventos_etapas = tabelas.ler_registros(grupo.eventos, com_responsavel=False, antigo=antigo) if grupo else eventos
    marcos, probs = etapas.identificar_etapas(chat, eventos_etapas, bloco.grupo if grupo else bloco.numero, antigo)
    r.problemas.extend(probs)
    if modo_norm in ("aberto", "fechado"):
        # etapa única: todos os lances são dela, exceto os que caem numa janela de desempate
        unica = etapas.ABERTA if modo_norm == "aberto" else etapas.FECHADA
        desempates = [j for j in marcos.janelas if j.etapa == etapas.DESEMPATE]
        classificados = [(l, etapas.DESEMPATE if any(j.contem(l.data_hora) for j in desempates) else unica) for l in lances]
        resolvidos = 0
    elif fechado_aberto:
        # a etapa fechada não tem lances na tabela (são as propostas); os lances são da etapa aberta, que
        # começa em "O item N foi aberto.", exceto os de uma janela de desempate
        desempates = [j for j in marcos.janelas if j.etapa == etapas.DESEMPATE]
        abertura = marcos.abertura or etapas.montar_etapas(
            chat, etapas.padroes_chat(bloco.grupo if grupo else bloco.numero), "chat do item").abertura
        if abertura is None:
            r.avisos.append("abertura da etapa aberta não encontrada no chat nem nos eventos: lances tomados como da etapa aberta")
        else:
            antes = [l for l in lances if not l.excluido and l.data_hora < abertura]
            if antes:
                r.problemas.append(f"{len(antes)} lance(s) antes da abertura da etapa aberta ({abertura:%d/%m/%Y %H:%M:%S})")
        classificados = [(l, etapas.DESEMPATE if any(j.contem(l.data_hora) for j in desempates) else etapas.ABERTA)
                         for l in lances]
        resolvidos = 0
    elif modo_norm == "aberto/fechado":
        if not marcos.fechadas():
            r.problemas.append("não foi possível identificar a etapa fechada no chat nem nos eventos do item")
            return
        if grupo:
            # a mensagem de encerramento traz totais do grupo: não serve para conferir valores do item
            r.problemas.extend(etapas.conferir_grupo(itens_do_grupo(documento, bloco.grupo), marcos))
            for j in marcos.janelas:
                j.lances_informados = None
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

    d["melhor_lance_modo_aberto"] = campos.mais_vantajoso(iniciais + [resumo.melhor[etapas.ABERTA]], criterio)
    if not fechado_aberto:
        d["melhor_lance_modo_fechado"] = resumo.melhor[etapas.FECHADA]
    d["melhor_lance_desempate"] = resumo.melhor[etapas.DESEMPATE]
    com_fechada = modo_norm == "aberto/fechado"
    abertos = abertos_iniciais + [(l.participante, l.valor, l.data_hora) for l, e in classificados
                                  if e == etapas.ABERTA and not l.excluido]
    fechados = [(l.participante, l.valor) for l, e in classificados if e == etapas.FECHADA and not l.excluido]
    preencher_lideranca(d, propostas, abertos, fechados, criterio, com_fechada)
    if fechado_aberto:
        preencher_fechada_das_propostas(d, propostas, criterio, r, avisar=False)
        if resumo.menor[etapas.ABERTA] is None:
            r.avisos.append("nenhum lance registrado na etapa aberta")
    if com_fechada:
        d["reinicios_etapa_fechada"] = marcos.reinicios_fechada
    if modo_norm == "aberto/fechado" and resumo.menor[etapas.FECHADA] is None:
        r.avisos.append("nenhum lance registrado na etapa fechada")
    if resumo.excluidos:
        r.avisos.append(f"{resumo.excluidos} lance(s) marcados como excluídos (*) desconsiderados")
    if lances and resumo.melhor[etapas.ABERTA] is None and resumo.menor[etapas.ABERTA] is not None:
        r.problemas.append(f"critério de julgamento do item não reconhecido ({criterio!r}): melhor lance não definido")
    r.fontes.append(
        f"lances: Lances do Item {bloco.numero} {bloco.lances.paginas}; etapas: {marcos.origem}"
    )
