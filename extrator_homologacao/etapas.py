"""Etapas da disputa (aberta, fechada, desempates) e classificação dos lances por etapa.

O relatório traz uma única tabela "Lances do Item N" com todos os lances, sem indicar a etapa.
A etapa de cada lance é determinada pelas janelas de tempo anunciadas no chat do item
("O item N foi aberto", "A etapa fechada foi iniciada/reiniciada...", "A etapa fechada do item N
foi encerrada..."). Os "Eventos do Item" servem de alternativa quando o chat não traz esses marcos.
As listas de valores que o chat informa ao encerrar uma etapa são usadas apenas para conferência,
nunca como lances.
"""

import re
from dataclasses import dataclass, field

from . import normalizacao as norm

ABERTA, FECHADA, DESEMPATE = "aberta", "fechada", "desempate"


@dataclass
class Janela:
    etapa: str
    descricao: str
    inicio: object  # datetime
    pagina: int
    fim: object = None
    lances_informados: list | None = None  # valores que a mensagem de encerramento diz terem sido registrados

    def contem(self, momento):
        return self.inicio <= momento and (self.fim is None or momento <= self.fim)


@dataclass
class Etapas:
    origem: str  # "chat do item" | "eventos do item"
    abertura: object = None
    janelas: list = field(default_factory=list)

    @property
    def inicio_fechada(self):
        inicios = [j.inicio for j in self.janelas if j.etapa == FECHADA]
        return min(inicios) if inicios else None

    def fechadas(self):
        return [j for j in self.janelas if j.etapa == FECHADA]


def padroes_chat(numero):
    n = numero
    return {
        "abertura": re.compile(rf"^O item {n} foi aberto\."),
        (FECHADA, "etapa fechada", "inicio"): re.compile(rf"^A etapa fechada foi (?:iniciada|reiniciada) para o item {n}\."),
        (FECHADA, "etapa fechada", "fim"): re.compile(rf"^A etapa fechada do item {n} foi encerrada\.(.*)"),
        (DESEMPATE, "desempate art. 60", "inicio"): re.compile(rf"^O desempate por disputa final do art\. ?60\b.*? foi iniciado para o item {n}\.", re.I),
        (DESEMPATE, "desempate art. 60", "fim"): re.compile(rf"^O desempate por disputa final do art\. ?60\b.*? do item {n} foi encerrado\.(.*)", re.I),
        (DESEMPATE, "desempate ME/EPP", "inicio"): re.compile(rf"^O item {n} terá desempate Me/Epp", re.I),
        (DESEMPATE, "desempate ME/EPP", "fim"): re.compile(rf"^O item {n} teve o \d+º desempate Me/Epp encerrado(.*)", re.I),
    }


PADROES_EVENTOS = {
    "abertura": re.compile(r"^Item aberto para lances\."),
    (FECHADA, "etapa fechada", "inicio"): re.compile(r"^(?:Início da etapa fechada\.|Retorno de item do Julgamento para a etapa fechada)"),
    (FECHADA, "etapa fechada", "fim"): re.compile(r"^Item com etapa fechada encerrada\.()"),
    (DESEMPATE, "desempate art. 60", "inicio"): re.compile(r"^Convocados os fornecedores me/epp declarantes para a disputa final do art\. ?60", re.I),
    (DESEMPATE, "desempate art. 60", "fim"): re.compile(r"^Item com etapa de disputa final do art\. ?60\b.*encerrada\.()", re.I),
    (DESEMPATE, "desempate ME/EPP", "inicio"): re.compile(r"^Item está em \d+º desempate Me/Epp", re.I),
    (DESEMPATE, "desempate ME/EPP", "fim"): re.compile(r"^Item teve o \d+º desempate Me/Epp encerrado()", re.I),
}


def lances_informados(resto):
    """Valores citados na mensagem de encerramento da etapa (apenas para conferência)."""
    if "Os seguintes lances foram registrados" in resto:
        return norm.valores(resto)
    if "Nenhum fornecedor convocado registrou lance" in resto:
        return []
    return None


def montar_etapas(registros, padroes, origem):
    etapas = Etapas(origem=origem)
    for r in sorted(registros, key=lambda r: r.data_hora):
        if etapas.abertura is None and padroes["abertura"].search(r.texto):
            etapas.abertura = r.data_hora
            continue
        for chave, padrao in padroes.items():
            if chave == "abertura":
                continue
            etapa, descricao, marco = chave
            m = padrao.search(r.texto)
            if not m:
                continue
            if marco == "inicio":
                etapas.janelas.append(Janela(etapa, descricao, r.data_hora, r.pagina))
            else:
                mesmas = [j for j in etapas.janelas if j.descricao == descricao]
                abertas = [j for j in mesmas if j.fim is None]
                # desempate ME/EPP tem várias rodadas (1º, 2º...) após um único anúncio no chat
                alvo = abertas[-1] if abertas else (mesmas[-1] if mesmas and descricao == "desempate ME/EPP" else None)
                if alvo is not None:
                    alvo.fim = r.data_hora
                    if m.groups():
                        alvo.lances_informados = lances_informados(m.group(1))
            break
    return etapas


def identificar_etapas(mensagens_chat, eventos, numero_item):
    """Retorna (etapas, problemas). Prefere o chat do item; usa os eventos como alternativa."""
    problemas = []
    do_chat = montar_etapas(mensagens_chat, padroes_chat(numero_item), "chat do item")
    dos_eventos = montar_etapas(eventos, PADROES_EVENTOS, "eventos do item")

    if do_chat.fechadas() and dos_eventos.fechadas():
        # o chat anuncia cada reinício da etapa fechada; os eventos às vezes os agrupam numa janela só
        if unir_contiguas(do_chat.fechadas()) != unir_contiguas(dos_eventos.fechadas()):
            problemas.append("janelas da etapa fechada divergem entre o chat e os eventos do item")
    etapas = do_chat if do_chat.fechadas() else dos_eventos

    for j in etapas.janelas:
        if j.fim is None:
            problemas.append(f"{j.descricao} iniciada em {j.inicio:%d/%m/%Y %H:%M:%S} sem registro de encerramento")
    return etapas, problemas


def unir_contiguas(janelas):
    """Intervalos (inicio, fim) com janelas encostadas/sobrepostas unidas."""
    unidas = []
    for j in sorted(janelas, key=lambda j: j.inicio):
        if unidas and unidas[-1][1] is not None and j.inicio <= unidas[-1][1]:
            fim = None if j.fim is None else max(unidas[-1][1], j.fim)
            unidas[-1] = (unidas[-1][0], fim)
        else:
            unidas.append((j.inicio, j.fim))
    return unidas


def candidatas(lance, etapas):
    """Etapas compatíveis com o horário do lance (mais de uma quando cai exatamente numa fronteira)."""
    resultado = set()
    inicio_fechada = etapas.inicio_fechada
    if inicio_fechada is not None and lance.data_hora <= inicio_fechada:
        if etapas.abertura is None or lance.data_hora >= etapas.abertura:
            resultado.add(ABERTA)
    for j in etapas.janelas:
        if j.contem(lance.data_hora):
            resultado.add(j.etapa)
    return resultado


def _valores(lances):
    return sorted(l.valor for l in lances if not l.excluido), sorted(l.valor for l in lances)


def classificar_lances(lances, etapas):
    """Retorna (lista de (lance, etapa|None), quantidade resolvida pela mensagem de encerramento).

    O horário dos lances tem resolução de segundos; um lance registrado no mesmo segundo em que a
    etapa fechada (ou um desempate) começa é compatível com duas etapas. Nesses casos, a lista de
    valores que a mensagem de encerramento da etapa informa decide a qual etapa o lance pertence;
    se ainda assim não fechar, o lance fica sem etapa (relatório vai para REVISAR).
    """
    cands = [candidatas(l, etapas) for l in lances]
    resolvidos = 0
    for j in etapas.janelas:
        if j.lances_informados is None:
            continue
        informados = sorted(j.lances_informados)
        certos = [l for l, c in zip(lances, cands) if c == {j.etapa} and j.contem(l.data_hora)]
        duvidosos = [i for i, (l, c) in enumerate(zip(lances, cands)) if len(c) > 1 and j.etapa in c and j.contem(l.data_hora)]
        if not duvidosos:
            continue
        com = _valores(certos + [lances[i] for i in duvidosos])
        sem = _valores(certos)
        if informados in com and informados not in sem:
            for i in duvidosos:
                cands[i] = {j.etapa}
                resolvidos += 1
        elif informados in sem and informados not in com:
            for i in duvidosos:
                cands[i] = cands[i] - {j.etapa}
                resolvidos += len(cands[i]) == 1
    return [(l, next(iter(c)) if len(c) == 1 else None) for l, c in zip(lances, cands)], resolvidos


def conferir_com_chat(classificados, etapas):
    """Compara os lances atribuídos a cada janela com os valores que a mensagem de encerramento informa."""
    problemas = []
    for j in etapas.janelas:
        if j.lances_informados is None:
            continue
        na_janela = [l for l, e in classificados if e == j.etapa and j.contem(l.data_hora)]
        validos, todos = _valores(na_janela)
        informados = sorted(j.lances_informados)
        if informados not in (validos, todos):
            problemas.append(
                f"{j.descricao} iniciada em {j.inicio:%d/%m/%Y %H:%M:%S}: tabela de lances tem "
                f"{len(validos)} lance(s) {[str(v) for v in validos]}, mensagem de encerramento informa "
                f"{[str(v) for v in informados]}"
            )
    return problemas
