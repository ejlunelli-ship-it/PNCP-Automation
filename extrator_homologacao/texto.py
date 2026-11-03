"""Extração do texto dos PDFs (PyMuPDF), com OCR opcional e limpeza de cabeçalho/rodapé de página.

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
