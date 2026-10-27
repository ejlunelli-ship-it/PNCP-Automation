"""Identificação das seções do relatório: cabeçalho da compra e, para cada item, o bloco do item,
as propostas, a tabela de lances, o chat do item e os eventos do item."""

import re
from dataclasses import dataclass, field

TIPOS_RELATORIO = ("TERMO DE HOMOLOGAÇÃO", "TERMO DE JULGAMENTO", "RELATÓRIO DE DILIGÊNCIAS")

RE_INICIO_ITEM = re.compile(r"^Item (\d+) - (.*)$")
# quantas linhas após "Item N - ..." procurar os rótulos que confirmam que é o bloco de um item
JANELA_CONFIRMA_ITEM = 60

# cabeçalhos de coluna que o relatório repete a cada página dentro das tabelas
COLUNAS_REPETIDAS = {
    "propostas": ("Fornecedor", "Valor ofertado", "Situação"),
    "lances": ("Data/hora", "Participante", "Lance"),
    "chat": ("Responsável", "Data/Hora", "Mensagem"),
    "eventos": ("Data/Hora", "Descrição"),
}


@dataclass
class Secao:
    nome: str
    linhas: list = field(default_factory=list)

    @property
    def textos(self):
        return [l.texto for l in self.linhas]

    @property
    def paginas(self):
        """Referência de páginas para auditoria, ex.: 'p.10-12'."""
        if not self.linhas:
            return ""
        ini, fim = self.linhas[0].pagina, self.linhas[-1].pagina
        return f"p.{ini}" if ini == fim else f"p.{ini}-{fim}"

    def __bool__(self):
        return bool(self.linhas)


@dataclass
class BlocoItem:
    numero: int
    cabecalho: Secao
    propostas: Secao
    lances: Secao
    chat: Secao
    eventos: Secao


@dataclass
class Documento:
    tipo: str | None
    cabecalho: Secao
    itens: dict  # numero -> BlocoItem


def remover_colunas_repetidas(linhas, colunas):
    n = len(colunas)
    saida, i = [], 0
    while i < len(linhas):
        if tuple(l.texto for l in linhas[i:i + n]) == colunas:
            i += n
            continue
        saida.append(linhas[i])
        i += 1
    return saida


def tipo_relatorio(linhas):
    for l in linhas[:10]:
        if l.texto in TIPOS_RELATORIO:
            return l.texto
    return None


def inicios_de_item(linhas):
    """Índices das linhas que abrem o bloco de um item (confirmados pelos rótulos do bloco)."""
    inicios = []
    for i, l in enumerate(linhas):
        if not RE_INICIO_ITEM.match(l.texto):
            continue
        janela = [x.texto for x in linhas[i + 1:i + 1 + JANELA_CONFIRMA_ITEM]]
        if "Quantidade:" in janela and "Valor estimado:" in janela:
            inicios.append(i)
    return inicios


def dividir_item(numero, linhas):
    """Divide as linhas de um item pelos títulos das subseções, na ordem em que aparecem."""
    titulos = {
        f"Propostas do Item {numero}": "propostas",
        f"Lances do Item {numero}": "lances",
        f"Mensagens do chat do Item {numero}": "chat",
        f"Eventos do Item {numero}": "eventos",
    }
    partes = {nome: Secao(nome) for nome in ("cabecalho", "propostas", "lances", "chat", "eventos")}
    atual = partes["cabecalho"]
    for l in linhas:
        if l.texto in titulos:
            atual = partes[titulos[l.texto]]
            continue
        if l.texto.startswith("Fase Recursal do Item"):
            atual = Secao("ignorada")
            continue
        atual.linhas.append(l)
    for nome, colunas in COLUNAS_REPETIDAS.items():
        partes[nome].linhas = remover_colunas_repetidas(partes[nome].linhas, colunas)
    return BlocoItem(numero=numero, **partes)


def segmentar(linhas):
    inicios = inicios_de_item(linhas)
    fim_cabecalho = len(linhas)
    for i, l in enumerate(linhas):
        if l.texto == "Mensagens do chat da compra":
            fim_cabecalho = i
            break
    if inicios:
        fim_cabecalho = min(fim_cabecalho, inicios[0])
    cabecalho = Secao("cabecalho", linhas[:fim_cabecalho])

    itens = {}
    for pos, ini in enumerate(inicios):
        fim = inicios[pos + 1] if pos + 1 < len(inicios) else len(linhas)
        numero = int(RE_INICIO_ITEM.match(linhas[ini].texto).group(1))
        if numero in itens:
            # o mesmo item duas vezes no documento: mantém o primeiro e deixa a validação acusar
            continue
        itens[numero] = dividir_item(numero, linhas[ini:fim])
    return Documento(tipo=tipo_relatorio(linhas), cabecalho=cabecalho, itens=itens)
