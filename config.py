"""Pasta onde os scripts gravam e leem os dados: variável de ambiente PNCP_DADOS ou ./dados do projeto."""
import os
from pathlib import Path

DADOS = Path(os.environ.get("PNCP_DADOS") or Path(__file__).parent / "dados")
