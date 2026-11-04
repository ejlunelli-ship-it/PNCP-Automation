"""Relatórios da compra publicados pelo próprio órgão no PNCP (sem captcha).

Alguns órgãos (ex.: Prefeitura de Fortaleza) anexam no PNCP os termos de homologação/julgamento
do Compras.gov.br, os mesmos que vêm no zip "Todos os relatórios e termos". Este módulo lista
os arquivos da contratação na API do PNCP, baixa os candidatos e guarda os que forem, pelo
conteúdo, termos dessa compra, com o nome que o zip usaria
(relatorio-termo-homologacao-<idCompra>-item-<N>.pdf), para o extrator tratá-los igual.

Esses órgãos costumam ter DUAS contratações no PNCP para o mesmo pregão: a que o Compras.gov.br
publica sozinho (a do get.py, só com o edital) e a do sistema do próprio órgão, com os demais
documentos. Por isso, além da própria contratação, são vasculhadas as "irmãs": mesmo CNPJ,
mesmo número de compra e data de abertura das propostas, publicadas por outro sistema.

Candidatos que o extrator não lê (outra plataforma, PDF escaneado, outro formato) não são
descartados: vão para a pasta `outros`, fora de relatorios/, com uma linha em manifesto.csv.
"""
import calendar
import csv
import io
import json
import re
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import pymupdf
import requests

from config import DADOS
from extrator_homologacao.campos import campos_cabecalho
from extrator_homologacao.secoes import segmentar
from extrator_homologacao.texto import linhas_limpas

API = "https://pncp.gov.br/api/pncp/v1"
CONSULTA = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
MODALIDADES_PNCP = (6, 7)  # Pregão Eletrônico e Presencial na codificação do PNCP
JANELA_IRMAS = 30          # dias antes/depois da publicação da compra para procurar as irmãs
RE_CONTROLE = re.compile(r"^(\d{14})-\d+-(\d+)/(\d{4})$")
# tipos de documento do PNCP (GET /v1/tipos-documentos): 26 Termo/Ato de Homologação e
# 27/28 Ata de sessão pública são sempre baixados; os demais (em geral 16 Outros Documentos)
# só se o título lembrar um termo. Edital, TR, ETP, minutas, pesquisa de preços etc. nunca.
TIPOS_CANDIDATOS = {26, 27, 28}
TIPOS_IGNORADOS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 19, 29, 30, 31, 32, 33, 34, 36, 39, 40}
RE_TITULO = re.compile(r"(?i)homolog|julg|(?<![a-zà-ú])ata(?![a-zà-ú])|atatotal|relat[oó]rio|termo|sess[aã]o|lance")
TAMANHO_MAXIMO = 50 * 1024 * 1024
RE_LANCES = re.compile(r"(?i)\blances?\b")
MIN_CARACTERES_POR_PAGINA = 40  # abaixo disso o PDF é tratado como escaneado
COLUNAS_MANIFESTO = ["numeroControlePNCP", "idCompra", "titulo", "tipoDocumentoId", "tipoDocumentoNome", "url",
                     "membro", "tamanho", "motivo", "guardado", "arquivo"]

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})


class FalhaAPI(Exception):
    """A consulta falhou depois das tentativas: não dá para dizer que o arquivo não existe."""


@dataclass
class Busca:
    """Resultado da busca de uma compra no PNCP."""
    cobertos: set = field(default_factory=set)
    publicados: int = 0   # arquivos listados na contratação e nas irmãs
    candidatos: int = 0   # arquivos que passaram pelo filtro de tipo e título
    guardados: int = 0    # arquivos gravados em `outros`
    erros: list = field(default_factory=list)

    @property
    def motivo(self):
        if self.cobertos:
            return "termos encontrados"
        if self.erros:
            return "erro na API"
        if not self.publicados:
            return "nenhum arquivo publicado"
        if not self.candidatos:
            return "nenhum candidato"
        return "outros formatos guardados" if self.guardados else "candidatos sem lances"


def _get(url, tentativas=3, exigir=False):
    """Resposta 200/204, ou None. Com `exigir`, falha de rede ou do servidor lança FalhaAPI."""
    for i in range(tentativas):
        try:
            r = session.get(url, timeout=90)
            if r.status_code in (200, 204):
                return r
            if r.status_code not in (429, 500, 502, 503, 504):
                return None
        except (requests.Timeout, requests.ConnectionError):
            pass
        time.sleep(2 ** i)
    if exigir:
        raise FalhaAPI(url)
    return None


def _partes(conteudo, nome):
    """(nome, bytes) do arquivo baixado; um zip com PDFs é aberto, e qualquer outro formato vem inteiro."""
    if zipfile.is_zipfile(io.BytesIO(conteudo)):
        try:
            with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
                membros = [m for m in z.infolist() if not m.is_dir() and m.file_size <= TAMANHO_MAXIMO]
                if any(m.filename.lower().endswith(".pdf") for m in membros):
                    return [(m.filename, z.read(m)) for m in membros]
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
            pass  # zip protegido ou corrompido: guarda o arquivo inteiro
    return [(nome, conteudo)]


def _motivo_para_guardar(dados):
    """Por que guardar um arquivo que o extrator não lê; None se for PDF legível sem menção a lances."""
    if dados[:4] != b"%PDF":
        return "formato não PDF"
    try:
        with pymupdf.open(stream=dados, filetype="pdf") as doc:
            paginas = [p.get_text() for p in doc]
    except Exception:
        return "PDF ilegível"
    texto = "".join(paginas)
    if len(texto.strip()) < MIN_CARACTERES_POR_PAGINA * max(len(paginas), 1):
        return "PDF sem texto"
    return "menciona lances" if RE_LANCES.search(texto) else None


def _registrar(outros, linha):
    outros.mkdir(parents=True, exist_ok=True)
    arquivo = outros / "manifesto.csv"
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_MANIFESTO, extrasaction="ignore")
        if novo:
            w.writeheader()
        w.writerow(linha)


def _guardar(outros, registro, ordem, nome, dados):
    """Grava em <outros>/<compra>/ com um nome que o seletor do extrator não confunde com um termo."""
    pasta = outros / f"{registro['numeroCompra']}-{registro['anoCompraPncp']}_{registro['idCompra']}"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = Path(re.sub(r"[\\/]+", "/", nome or "arquivo"))
    extensao = ".pdf" if dados[:4] == b"%PDF" else (caminho.suffix[:8] or ".bin")
    saida = pasta / f"{ordem:03d}-{re.sub(r'[^\w.-]+', '_', caminho.stem)[:80]}{extensao}"
    saida.write_bytes(dados)
    return saida


def _identificar(pdf, id_compra):
    """(tipo, itens) se o PDF for termo de homologação/julgamento desta compra; senão None."""
    try:
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            paginas = [p.get_text() for p in doc]
    except Exception:
        return None
    documento = segmentar(linhas_limpas(paginas))
    if documento.tipo not in ("TERMO DE HOMOLOGAÇÃO", "TERMO DE JULGAMENTO") or not documento.itens:
        return None
    cab = campos_cabecalho(documento.cabecalho)
    # idCompra = UASG + modalidade + número + ano (ex.: 927744 05 90120 2025)
    numero = re.sub(r"\D", "", cab.get("pregao") or cab.get("numero_compra") or "")
    if not (cab.get("uasg") and numero and id_compra.startswith(cab["uasg"]) and id_compra.endswith(numero)):
        return None
    return documento.tipo, sorted(documento.itens)


def quantidade_itens(registro):
    """Número de itens da contratação no PNCP, ou None se não der para saber."""
    m = RE_CONTROLE.match(registro.get("numeroControlePNCP") or "")
    if not m:
        return None
    cnpj, seq, ano = m.groups()
    r = _get(f"{API}/orgaos/{cnpj}/compras/{ano}/{int(seq)}/itens/quantidade")
    try:
        return int(r.text) if r is not None and r.status_code == 200 else None
    except ValueError:
        return None


_publicadas = {}  # (cnpj, modalidade, data inicial, data final) -> contratações do PNCP
_listas_com_falha = set()  # mesmas chaves: não repete, a cada compra do órgão, uma lista que já falhou


def _publicadas_no_periodo(cnpj, inicio, fim):
    """Contratações de pregão do órgão publicadas no PNCP no período (consulta paginada, em cache)."""
    todas = []
    for modalidade in MODALIDADES_PNCP:
        chave = (cnpj, modalidade, inicio, fim)
        if chave in _listas_com_falha:
            raise FalhaAPI(f"lista do órgão {cnpj} já falhou nesta rodada")
        if chave not in _publicadas:
            lista, pagina = [], 1
            while True:
                try:
                    r = _get(f"{CONSULTA}?dataInicial={inicio:%Y%m%d}&dataFinal={fim:%Y%m%d}&cnpj={cnpj}"
                             f"&codigoModalidadeContratacao={modalidade}&pagina={pagina}&tamanhoPagina=50", exigir=True)
                except FalhaAPI:
                    _listas_com_falha.add(chave)
                    raise
                if r is None or r.status_code == 204 or not r.content:
                    break
                j = r.json()
                lista += j.get("data") or []
                if pagina >= (j.get("totalPaginas") or 1):
                    break
                pagina += 1
            _publicadas[chave] = lista
        todas += _publicadas[chave]
    return todas


def _numero(texto):
    """Número da compra sem ano/zeros à esquerda: '90120/2025' e '90120' -> '90120'."""
    return re.sub(r"\D", "", str(texto or "").split("/")[0]).lstrip("0")


class IndicePublicadas:
    """Pregões Aberto-Fechado publicados no PNCP por mês, em dados/pncp_publicadas/<AAAA-MM>.json.

    Lista cada mês uma vez, para todos os órgãos, o que é muito mais barato que consultar órgão por
    órgão. Só o modo Aberto-Fechado: corta 3/4 das páginas, e as irmãs conferidas têm o mesmo modo.
    Vai devagar de propósito: o PNCP responde 429 depois de umas 9 requisições seguidas.
    """
    PASTA = DADOS / "pncp_publicadas"
    ESPERA_PAGINA = 2
    MODO_ABERTO_FECHADO = 3

    def __init__(self):
        self.por_chave = defaultdict(list)
        self.meses = set()

    def _pagina(self, params):
        for i in range(8):
            try:
                r = session.get(CONSULTA, params=params, timeout=120)
                if r.status_code in (200, 204):
                    return r
                if r.status_code == 429:
                    espera = int(r.headers.get("Retry-After") or 20 * (i + 1))
                    print(f"  PNCP pediu para esperar ({espera}s)", flush=True)
                    time.sleep(espera)
                    continue
                if r.status_code not in (500, 502, 503, 504):
                    break
            except (requests.Timeout, requests.ConnectionError):
                pass
            time.sleep(5 * 2 ** i)
        raise FalhaAPI(f"{CONSULTA} {params}")

    def _baixar(self, ano_mes):
        ano, mes = map(int, ano_mes.split("-"))
        fim = calendar.monthrange(ano, mes)[1]
        registros = []
        for modalidade in MODALIDADES_PNCP:
            pagina = 1
            while True:
                r = self._pagina({"dataInicial": f"{ano}{mes:02d}01", "dataFinal": f"{ano}{mes:02d}{fim}",
                                  "codigoModalidadeContratacao": modalidade, "codigoModoDisputa": self.MODO_ABERTO_FECHADO,
                                  "pagina": pagina, "tamanhoPagina": 50})
                if r.status_code == 204 or not r.content:
                    break
                j = r.json()
                registros += [{"numeroControlePNCP": x.get("numeroControlePNCP"), "cnpj": (x.get("orgaoEntidade") or {}).get("cnpj"),
                               "anoCompra": x.get("anoCompra"), "sequencialCompra": x.get("sequencialCompra"),
                               "numeroCompra": x.get("numeroCompra"), "dataAberturaProposta": x.get("dataAberturaProposta"),
                               "usuarioNome": x.get("usuarioNome")} for x in j.get("data") or []]
                if pagina >= (j.get("totalPaginas") or 1):
                    break
                if pagina % 100 == 0:
                    print(f"  índice {ano_mes}: página {pagina}/{j.get('totalPaginas')}", flush=True)
                pagina += 1
                time.sleep(self.ESPERA_PAGINA)
        return registros

    def carregar(self, ano_mes):
        if ano_mes in self.meses:
            return
        arquivo = self.PASTA / f"{ano_mes}.json"
        if arquivo.exists():
            registros = json.loads(arquivo.read_text(encoding="utf-8"))
        else:
            registros = self._baixar(ano_mes)
            if ano_mes < f"{date.today():%Y-%m}":  # mês em aberto ainda muda: não fica gravado
                self.PASTA.mkdir(parents=True, exist_ok=True)
                arquivo.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
            print(f"  índice {ano_mes}: {len(registros)} contratações", flush=True)
        for c in registros:
            self.por_chave[(c["cnpj"], str(c["anoCompra"]), _numero(c["numeroCompra"]))].append(c)
        self.meses.add(ano_mes)

    def irmas(self, registro, cnpj, ano):
        """Sequenciais das contratações com mesmo CNPJ, ano, número e abertura desta compra."""
        abertura = registro.get("dataAberturaPropostaPncp")
        return sorted({c["sequencialCompra"] for c in self.por_chave[(cnpj, ano, _numero(registro.get("numeroCompra")))]
                       if c["numeroControlePNCP"] != registro["numeroControlePNCP"]
                       and not (abertura and c["dataAberturaProposta"] and c["dataAberturaProposta"] != abertura)})


def contratacoes_candidatas(registro, irmas=True, indice=None):
    """(cnpj, ano, sequencial) da própria contratação e, com `irmas`, das publicadas por outro sistema."""
    m = RE_CONTROLE.match(registro.get("numeroControlePNCP") or "")
    if not m:
        return []
    cnpj, seq, ano = m.groups()
    candidatas = [(cnpj, ano, int(seq))]
    if not irmas:
        return candidatas
    if indice is not None:
        return candidatas + [(cnpj, ano, int(s)) for s in indice.irmas(registro, cnpj, ano)]
    try:
        publicada = datetime.fromisoformat(registro["dataPublicacaoPncp"]).date()
    except (KeyError, TypeError, ValueError):
        return candidatas
    janela = timedelta(days=JANELA_IRMAS)
    # janela alinhada ao mês, para o cache servir a todas as compras do mesmo mês
    inicio = (publicada.replace(day=1) - janela).replace(day=1)
    fim = publicada.replace(day=1) + timedelta(days=31) + janela
    numero, abertura = _numero(registro.get("numeroCompra")), registro.get("dataAberturaPropostaPncp")
    for c in _publicadas_no_periodo(cnpj, inicio, fim):
        if (c.get("numeroControlePNCP") == registro["numeroControlePNCP"]
                or str(c.get("anoCompra")) != ano
                or _numero(c.get("numeroCompra")) != numero
                or (abertura and c.get("dataAberturaProposta") and c["dataAberturaProposta"] != abertura)):
            continue
        candidatas.append((cnpj, ano, int(c["sequencialCompra"])))
    return candidatas


def baixar_do_pncp(registro, destino, outros=None, irmas=True, indice=None):
    """Grava em `destino` os termos desta compra encontrados no PNCP e, em `outros`, os demais
    candidatos que possam ter lances. Devolve a Busca, com os itens cobertos e o motivo."""
    id_compra = str(registro["idCompra"])
    busca = Busca()
    try:
        contratacoes = contratacoes_candidatas(registro, irmas, indice)
    except FalhaAPI as e:
        busca.erros.append(f"irmãs: {e}")
        contratacoes = contratacoes_candidatas(registro, irmas=False)
    arquivos = []
    for cnpj, ano, seq in contratacoes:
        try:
            r = _get(f"{API}/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos", exigir=True)
        except FalhaAPI as e:
            busca.erros.append(f"lista: {e}")
            continue
        if r is not None and r.status_code == 200 and r.content:
            arquivos += r.json()
    busca.publicados = len(arquivos)

    for arq in arquivos:
        tipo_doc = arq.get("tipoDocumentoId")
        if tipo_doc in TIPOS_IGNORADOS or (tipo_doc not in TIPOS_CANDIDATOS
                                           and not RE_TITULO.search(arq.get("titulo") or "")):
            continue
        busca.candidatos += 1
        linha = {"numeroControlePNCP": registro.get("numeroControlePNCP"), "idCompra": id_compra,
                 "titulo": arq.get("titulo"), "tipoDocumentoId": tipo_doc,
                 "tipoDocumentoNome": arq.get("tipoDocumentoNome"), "url": arq.get("url"), "guardado": "não"}
        try:
            baixado = _get(arq["url"], exigir=True)
        except FalhaAPI as e:
            busca.erros.append(f"download: {e}")
            continue
        if baixado is None or not baixado.content or len(baixado.content) > TAMANHO_MAXIMO:
            tamanho = len(baixado.content) if baixado is not None else 0
            if outros:
                _registrar(outros, {**linha, "tamanho": tamanho,
                                    "motivo": "acima do limite" if tamanho else "download indisponível"})
            continue
        for nome, pdf in _partes(baixado.content, arq.get("titulo") or ""):
            achado = _identificar(pdf, id_compra) if pdf[:4] == b"%PDF" else None
            if not achado:
                if outros:
                    motivo = _motivo_para_guardar(pdf)
                    saida = None
                    if motivo:
                        busca.guardados += 1
                        saida = _guardar(outros, registro, busca.guardados, nome, pdf)
                    _registrar(outros, {**linha, "membro": nome, "tamanho": len(pdf),
                                        "motivo": motivo or "sem menção a lances",
                                        "guardado": "sim" if saida else "não", "arquivo": saida or ""})
                continue
            tipo, itens = achado
            for item in itens:
                if tipo == "TERMO DE HOMOLOGAÇÃO":
                    saida = f"relatorio-termo-homologacao-{id_compra}-item-{item}.pdf"
                else:
                    # a sessão não aparece no PDF; s0 perde para qualquer julgamento vindo do zip
                    saida = f"relatorio-julg-hab-{id_compra}-s0-item-{item}.pdf"
                destino.mkdir(parents=True, exist_ok=True)
                (destino / saida).write_bytes(pdf)
                busca.cobertos.add(item)
            print(f"  PNCP: {arq.get('titulo') or nome} -> {tipo.lower()}, itens {itens}")
        time.sleep(0.2)
    return busca
