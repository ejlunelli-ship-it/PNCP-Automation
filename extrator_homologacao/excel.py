"""Geração do Excel consolidado (pandas + openpyxl)."""

from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.utils import get_column_letter

from . import VERSAO_PARSER
from .validacao import COLUNAS, OK

COLUNAS_MONETARIAS = {c for c in COLUNAS if c.startswith(("valor_", "melhor_lance")) or c == "lance_aceito"}
FORMATO_MOEDA = '#,##0.0000'
LARGURA_MAX = 60


def para_dataframe(registros):
    linhas = [r.model_dump() for r in registros]
    df = pd.DataFrame(linhas, columns=COLUNAS)
    # mantém Decimal (precisão) e None (célula vazia); o openpyxl grava Decimal como número
    return df.astype(object).where(df.notna(), None)


def _formatar(ws, df):
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for i, coluna in enumerate(df.columns, start=1):
        letra = get_column_letter(i)
        amostra = [len(str(coluna))] + [len(str(v)) for v in df[coluna].head(200) if v is not None]
        ws.column_dimensions[letra].width = min(max(amostra) + 2, LARGURA_MAX)
        if coluna in COLUNAS_MONETARIAS:
            for celula in ws[letra][1:]:
                celula.number_format = FORMATO_MOEDA


def gerar_excel(registros, destino):
    """Planilha 'relatorios' (uma linha por PDF), 'revisar' (status != OK) e 'metadados'."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    df = para_dataframe(registros)
    revisar = df[df["status_extracao"] != OK]
    meta = pd.DataFrame([
        ("versao_parser", VERSAO_PARSER),
        ("gerado_em", datetime.now().replace(microsecond=0).isoformat()),
        ("total_pdfs", len(df)),
        *[(f"status_{s}", int(n)) for s, n in df["status_extracao"].value_counts().items()],
        ("observacao", "valores monetários unitários em R$; vazio = não informado/não identificado (nunca zero)"),
    ], columns=["chave", "valor"])

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for nome, tabela in (("relatorios", df), ("revisar", revisar)):
            tabela.to_excel(writer, sheet_name=nome, index=False)
            _formatar(writer.sheets[nome], tabela)
        meta.to_excel(writer, sheet_name="metadados", index=False)
    return destino
