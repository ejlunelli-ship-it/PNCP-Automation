"""Extração do texto dos PDFs (PyMuPDF), com OCR opcional e limpeza de cabeçalho/rodapé de página.
No layout antigo (ver `layouts`), o texto é refeito na ordem visual da página (`paginas_em_ordem_visual`).

O OCR é o do próprio PyMuPDF e só precisa do idioma: por.traineddata em dados/tessdata (baixe de
https://github.com/tesseract-ocr/tessdata_fast) ou na pasta da variável TESSDATA_PREFIX.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from config import DADOS

log = logging.getLogger(__name__)

DPI_OCR = 300

# abaixo disso por página consideramos que o PDF não tem camada de texto utilizável
MIN_CARACTERES_POR_PAGINA = 40

RE_CABECALHO_UASG = re.compile(r"^UASG \d+$")
RE_CABECALHO_PREGAO = re.compile(r"^[A-ZÀ-Ú][A-ZÀ-Ú ]* \d[\d./-]*$")  # "PREGÃO 96005/2026", "CONCORRÊNCIA ..."
RE_RODAPE_PAGINA = re.compile(r"^\d+ de \d+$")
RE_RODAPE_EMISSAO = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")


class SemTextoError(Exception):
    """PDF sem camada de texto e sem OCR disponível/habilitado."""


@dataclass(frozen=True)
class Linha:
    pagina: int  # 1-based
    texto: str


def paginas_do_pdf(caminho):
    with pymupdf.open(caminho) as doc:
        return [pagina.get_text() for pagina in doc]


def tem_texto_utilizavel(paginas):
    if not paginas:
        return False
    total = sum(len(p.strip()) for p in paginas)
    return total >= MIN_CARACTERES_POR_PAGINA * len(paginas)


def pasta_tessdata():
    return Path(os.environ.get("TESSDATA_PREFIX") or DADOS / "tessdata")


def ocr_disponivel():
    return (pasta_tessdata() / "por.traineddata").is_file()


def paginas_com_ocr(caminho):
    """Texto de cada página pelo OCR do PyMuPDF (Tesseract embutido, português)."""
    with pymupdf.open(caminho) as doc:
        paginas = []
        for pagina in doc:
            camada = pagina.get_textpage_ocr(language="por", dpi=DPI_OCR, full=True, tessdata=str(pasta_tessdata()))
            paginas.append(pagina.get_text(textpage=camada))
        return paginas


def extrair_paginas(caminho, ocr=True):
    """Texto de cada página. Retorna (paginas, usou_ocr)."""
    paginas = paginas_do_pdf(caminho)
    if tem_texto_utilizavel(paginas):
        return paginas, False
    if not ocr:
        raise SemTextoError("PDF sem camada de texto utilizável e OCR desabilitado")
    if not ocr_disponivel():
        raise SemTextoError(f"PDF sem camada de texto utilizável e sem por.traineddata em {pasta_tessdata()}")
    log.info("aplicando OCR em %s", caminho)
    paginas = paginas_com_ocr(caminho)
    if not tem_texto_utilizavel(paginas):
        raise SemTextoError("OCR não produziu texto utilizável")
    return paginas, True


# --------------------------------------------------------------------------- ordem visual (layout antigo)

# linhas da mesma célula separadas por mais que isso (pt) na vertical são linhas de células diferentes
# (as linhas de um parágrafo ficam a ~1,5 pt; as linhas de uma grade de rótulos, a ~6 pt)
DISTANCIA_LINHAS_CELULA = 3.0
# células que se sobrepõem na vertical mais que isso (pt) ficam na mesma faixa
SOBREPOSICAO_FAIXA = 1.0


def _linhas_do_bloco(bloco):
    """(bbox, texto) das linhas de um bloco do PyMuPDF.

    Num parágrafo justificado, o PDF antigo posiciona as palavras uma a uma e cada palavra vira uma
    linha do PyMuPDF terminada em espaço ("Adjucado ", "e ", "Homologado ", ...): as palavras
    seguidas na mesma altura voltam a formar uma linha só."""
    linhas = []
    for linha in bloco["lines"]:
        texto = "".join(s["text"] for s in linha["spans"])
        x0, y0, x1, y1 = linha["bbox"]
        if linhas:
            (a0, b0, a1, b1), anterior = linhas[-1]
            if anterior.endswith(" ") and abs(b0 - y0) < 1 and x0 >= a1:
                linhas[-1] = ((a0, min(b0, y0), x1, max(b1, y1)), anterior + texto)
                continue
        linhas.append(((x0, y0, x1, y1), texto))
    return [(bbox, texto.strip()) for bbox, texto in linhas if texto.strip()]


def _celulas(bloco):
    """Linhas de um bloco do PyMuPDF agrupadas em células: linhas que se sobrepõem na horizontal e
    estão encostadas na vertical (um parágrafo, um nome quebrado em várias linhas)."""
    celulas = []
    for (x0, y0, x1, y1), texto in _linhas_do_bloco(bloco):
        alvo = next((c for c in celulas if x0 < c["x1"] and c["x0"] < x1
                     and y0 - c["y1"] <= DISTANCIA_LINHAS_CELULA and c["y0"] - y1 <= DISTANCIA_LINHAS_CELULA), None)
        if alvo is None:
            celulas.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "linhas": [(y0, texto)]})
            continue
        alvo["linhas"].append((y0, texto))
        alvo["x0"], alvo["y0"] = min(alvo["x0"], x0), min(alvo["y0"], y0)
        alvo["x1"], alvo["y1"] = max(alvo["x1"], x1), max(alvo["y1"], y1)
    return celulas


def texto_em_ordem_visual(pagina):
    """Texto da página na ordem de leitura, uma linha por linha do PDF.

    Faixas de cima para baixo (células que se sobrepõem na vertical formam uma faixa: rótulo e valor,
    ou "Sistema", data/hora e mensagem de uma linha do chat); em cada faixa, as células da esquerda
    para a direita; em cada célula, as linhas de cima para baixo. O rodapé sai como no layout atual,
    "N de M" antes da data de emissão.
    """
    celulas = []
    for bloco in pagina.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)["blocks"]:
        if bloco.get("type") == 0:
            celulas.extend(_celulas(bloco))
    faixas = []
    for c in sorted(celulas, key=lambda c: (c["y0"], c["x0"])):
        if faixas and c["y0"] < faixas[-1]["y1"] - SOBREPOSICAO_FAIXA:
            faixas[-1]["celulas"].append(c)
            faixas[-1]["y1"] = max(faixas[-1]["y1"], c["y1"])
        else:
            faixas.append({"y1": c["y1"], "celulas": [c]})
    linhas = [texto for f in faixas for c in sorted(f["celulas"], key=lambda c: (c["x0"], c["y0"]))
              for _, texto in sorted(c["linhas"], key=lambda l: l[0])]
    if len(linhas) >= 2 and RE_RODAPE_EMISSAO.match(linhas[-2]) and RE_RODAPE_PAGINA.match(linhas[-1]):
        linhas[-2], linhas[-1] = linhas[-1], linhas[-2]
    return "\n".join(linhas)


def paginas_em_ordem_visual(caminho):
    """Texto de cada página na ordem de leitura (ver `texto_em_ordem_visual`)."""
    with pymupdf.open(caminho) as doc:
        return [texto_em_ordem_visual(pagina) for pagina in doc]


def linhas_limpas(paginas):
    """Linhas não vazias de todas as páginas, sem o cabeçalho repetido (UASG/PREGÃO) e o rodapé
    ("N de M" + data de emissão) que o relatório imprime em cada página."""
    linhas = []
    for numero, texto in enumerate(paginas, start=1):
        brutas = [l.strip() for l in texto.split("\n")]
        brutas = [l for l in brutas if l]
        if numero > 1 and len(brutas) >= 2 and RE_CABECALHO_UASG.match(brutas[0]) and RE_CABECALHO_PREGAO.match(brutas[1]):
            brutas = brutas[2:]
        if len(brutas) >= 2 and RE_RODAPE_PAGINA.match(brutas[-2]) and RE_RODAPE_EMISSAO.match(brutas[-1]):
            brutas = brutas[:-2]
        linhas.extend(Linha(numero, l) for l in brutas)
    return linhas
