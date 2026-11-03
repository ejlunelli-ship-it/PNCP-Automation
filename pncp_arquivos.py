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
"""
import io
import re
import time
import zipfile
from datetime import datetime, timedelta

import pymupdf
import requests

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
RE_TITULO = re.compile(r"(?i)homolog|julg|\bata\b|relat[oó]rio|termo|sess[aã]o")
TAMANHO_MAXIMO = 50 * 1024 * 1024

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})


def _get(url, tentativas=3):
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
    return None


def _pdfs(conteudo, nome):
    """PDFs dentro do arquivo baixado: o próprio PDF ou os PDFs de um zip."""
    if conteudo[:4] == b"%PDF":
        yield nome, conteudo
    elif zipfile.is_zipfile(io.BytesIO(conteudo)):
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for membro in z.namelist():
                if membro.lower().endswith(".pdf"):
                    yield membro, z.read(membro)


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


def _publicadas_no_periodo(cnpj, inicio, fim):
    """Contratações de pregão do órgão publicadas no PNCP no período (consulta paginada, em cache)."""
    todas = []
    for modalidade in MODALIDADES_PNCP:
        chave = (cnpj, modalidade, inicio, fim)
        if chave not in _publicadas:
            lista, pagina = [], 1
            while True:
                r = _get(f"{CONSULTA}?dataInicial={inicio:%Y%m%d}&dataFinal={fim:%Y%m%d}&cnpj={cnpj}"
                         f"&codigoModalidadeContratacao={modalidade}&pagina={pagina}&tamanhoPagina=50")
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


def contratacoes_candidatas(registro):
    """(cnpj, ano, sequencial) da própria contratação e das irmãs publicadas por outro sistema."""
    m = RE_CONTROLE.match(registro.get("numeroControlePNCP") or "")
    if not m:
        return []
    cnpj, seq, ano = m.groups()
    candidatas = [(cnpj, ano, int(seq))]
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


def baixar_do_pncp(registro, destino):
    """Grava em `destino` os termos desta compra encontrados no PNCP. Devolve os itens cobertos."""
    id_compra = str(registro["idCompra"])
    arquivos = []
    for cnpj, ano, seq in contratacoes_candidatas(registro):
        r = _get(f"{API}/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos")
        if r is not None and r.status_code == 200 and r.content:
            arquivos += r.json()

    cobertos = set()
    for arq in arquivos:
        tipo_doc = arq.get("tipoDocumentoId")
        if tipo_doc in TIPOS_IGNORADOS or (tipo_doc not in TIPOS_CANDIDATOS
                                           and not RE_TITULO.search(arq.get("titulo") or "")):
            continue
        baixado = _get(arq["url"])
        if baixado is None or not baixado.content or len(baixado.content) > TAMANHO_MAXIMO:
            continue
        for nome, pdf in _pdfs(baixado.content, arq.get("titulo") or ""):
            achado = _identificar(pdf, id_compra)
            if not achado:
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
                cobertos.add(item)
            print(f"  PNCP: {arq.get('titulo') or nome} -> {tipo.lower()}, itens {itens}")
        time.sleep(0.2)
    return cobertos
