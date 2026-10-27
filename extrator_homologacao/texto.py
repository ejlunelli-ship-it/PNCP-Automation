"""Extração do texto dos PDFs (PyMuPDF), com OCR opcional e limpeza de cabeçalho/rodapé de página."""

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pymupdf

log = logging.getLogger(__name__)

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


def ocr_disponivel():
    return shutil.which("ocrmypdf") is not None and shutil.which("tesseract") is not None


def paginas_com_ocr(caminho):
    """Roda OCRmyPDF (Tesseract, português) numa cópia temporária e extrai o texto resultante."""
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "ocr.pdf"
        subprocess.run(
            ["ocrmypdf", "--force-ocr", "-l", "por", "--quiet", str(caminho), str(saida)],
            check=True,
            capture_output=True,
        )
        return paginas_do_pdf(saida)


def extrair_paginas(caminho, ocr=True):
    """Texto de cada página. Retorna (paginas, usou_ocr)."""
    paginas = paginas_do_pdf(caminho)
    if tem_texto_utilizavel(paginas):
        return paginas, False
    if not ocr:
        raise SemTextoError("PDF sem camada de texto utilizável e OCR desabilitado")
    if not ocr_disponivel():
        raise SemTextoError("PDF sem camada de texto utilizável e OCRmyPDF/Tesseract não instalados")
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
