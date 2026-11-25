"""Validação técnica AUTOMÁTICA da cesta padronizada (modo operacional novo; não substitui nem altera o fluxo de
revisão humana, que continua em scripts/preparar_revisao.py e scripts/validar_revisao.py).

Status próprios (AUTO_*), nunca confundidos com aprovação humana. Regras determinísticas, versionadas e conservadoras:
aprova só quando a equivalência técnica é demonstrável por atributos objetivos e evidências verificáveis.
"""
VERSAO_VALIDADOR = "2.0.0"

AUTO_VALIDADO_CATALOGO = "AUTO_VALIDADO_CATALOGO"
AUTO_VALIDADO_CATALOGO_RESSALVA = "AUTO_VALIDADO_CATALOGO_COM_RESSALVA"   # S2: não é validação rigorosa
AUTO_VALIDADO_ITEM = "AUTO_VALIDADO_ITEM"
AUTO_INCONCLUSIVO = "AUTO_INCONCLUSIVO"
AUTO_DIVERGENTE = "AUTO_DIVERGENTE"
AUTO_DESMEMBRAR = "AUTO_DESMEMBRAR"
AUTO_ERRO_DADOS = "AUTO_ERRO_DADOS"
ITEM_SEM_VALIDACAO_DOCUMENTAL = "ITEM_SEM_VALIDACAO_DOCUMENTAL"
ITEM_SEM_CLASSIFICACAO = "ITEM_SEM_CLASSIFICACAO"
