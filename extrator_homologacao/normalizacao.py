"""Conversão de textos do relatório em tipos Python (Decimal, datetime, documentos)."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

RE_DATA_HORA = re.compile(r"^(\d{2}/\d{2}/\d{4}) às (\d{2}:\d{2}:\d{2})$")
RE_VALOR = re.compile(r"R\$\s*([\d.]+,\d+)")
# CNPJ (00.000.000/0000-00) ou CPF (000.000.000-00)
RE_DOCUMENTO = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}")


def espacos(texto):
    """Junta quebras de linha e remove espaços redundantes, sem alterar o conteúdo."""
    return re.sub(r"\s+", " ", texto).strip()


def juntar_quebras(texto):
    """Desfaz quebras que o PDF insere no meio de documentos e valores.

    Ex.: "07.400.977/0001-\\n45" -> "07.400.977/0001-45" e "R$\\n42,3000" -> "R$ 42,3000".
    """
    texto = re.sub(r"(\d)-\s+(\d)", r"\1-\2", texto)
    return espacos(texto)


def valor(texto):
    """'R$ 1.234,5600' -> Decimal('1234.5600'). Retorna None se não houver valor."""
    if texto is None:
        return None
    m = RE_VALOR.search(texto)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def valores(texto):
    """Todos os valores monetários de um trecho, na ordem em que aparecem."""
    return [Decimal(v.replace(".", "").replace(",", ".")) for v in RE_VALOR.findall(texto)]


def data_hora(texto):
    """'03/02/2026 às 09:11:40' -> datetime. Retorna None se não for uma data/hora."""
    m = RE_DATA_HORA.match(texto.strip())
    if not m:
        return None
    return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d/%m/%Y %H:%M:%S")


def documento(texto):
    """Primeiro CNPJ/CPF encontrado no texto (formatado), ou None."""
    m = RE_DOCUMENTO.search(texto or "")
    return m.group(0) if m else None


def digitos(texto):
    return re.sub(r"\D", "", texto or "")
