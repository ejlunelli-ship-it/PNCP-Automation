"""Modelo de dados da linha da planilha (pydantic) e validações de negócio."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

OK, REVISAR, ERRO = "OK", "REVISAR", "ERRO"

Dinheiro = Annotated[Decimal, Field(ge=0)]

RE_PREGAO_VALIDO = re.compile(r"^\d+/\d{4}$")


class RegistroExtracao(BaseModel):
    """Uma linha da planilha = um PDF. Valores ausentes são None (célula vazia), nunca zero."""

    model_config = ConfigDict(extra="forbid")

    # campos de negócio
    uasg: str | None = None
    pregao: str | None = None
    modo_disputa: str | None = None
    valor_estimado: Dinheiro | None = None
    melhor_lance_modo_aberto: Dinheiro | None = None
    melhor_lance_modo_fechado: Dinheiro | None = None
    quantidade_fornecedores: Annotated[int, Field(ge=0)] | None = None
    descricao_item: str | None = None
    lance_aceito: Dinheiro | None = None
    fornecedor_lance_aceito: str | None = None
    cnpj_fornecedor_lance_aceito: str | None = None
    situacao_lance_aceito: str | None = None

    # complementares, para auditoria
    pasta: str | None = None              # subpasta de origem (ex.: pregao_aberto-fechado)
    modalidade_compra: str | None = None  # ex.: PREGÃO, CONCORRÊNCIA
    numero_compra: str | None = None
    item: int | None = None
    tipo_relatorio: str | None = None
    situacao_item: str | None = None
    criterio_julgamento_item: str | None = None
    valor_estimado_total: Dinheiro | None = None
    melhor_lance_desempate: Dinheiro | None = None
    valor_negociado_aceito: Dinheiro | None = None
    lances_excluidos: Annotated[int, Field(ge=0)] | None = None
    fontes_extracao: str | None = None

    # técnicos
    arquivo_origem: str
    status_extracao: str = OK
    erros_extracao: str | None = None
    hash_arquivo: str | None = None
    versao_parser: str | None = None
    processado_em: datetime | None = None
    usou_ocr: bool | None = None


COLUNAS = list(RegistroExtracao.model_fields)


def validar(dados):
    """Regras de negócio sobre os campos extraídos. Retorna a lista de problemas (motivos de REVISAR)."""
    problemas = []
    uasg = dados.get("uasg")
    if not uasg:
        problemas.append("UASG ausente")
    elif not uasg.isdigit():
        problemas.append(f"UASG não numérica: {uasg!r}")

    numero = dados.get("numero_compra")
    rotulo = "pregão" if dados.get("modalidade_compra") == "PREGÃO" else "número da compra"
    if not numero:
        problemas.append(f"{rotulo} ausente")
    elif not RE_PREGAO_VALIDO.match(numero):
        problemas.append(f"{rotulo} em formato não reconhecido: {numero!r}")

    if not dados.get("modo_disputa"):
        problemas.append("modo de disputa não identificado no cabeçalho")

    if not dados.get("descricao_item"):
        problemas.append("descrição do item não identificada")

    qtd = dados.get("quantidade_fornecedores")
    if qtd is not None and (not isinstance(qtd, int) or qtd < 0):
        problemas.append(f"quantidade de fornecedores inválida: {qtd!r}")

    for campo in COLUNAS:
        v = dados.get(campo)
        if isinstance(v, Decimal) and v < 0:
            problemas.append(f"{campo} negativo: {v}")
    return problemas
