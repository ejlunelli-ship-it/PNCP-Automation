"""Extração conservadora de atributos objetivos das descrições (expressões regulares).

Opera sobre o texto normalizado (maiúsculas, sem acento). Cada atributo devolve valores canônicos
(número com ponto decimal e unidade padronizada). Nenhuma similaridade textual é usada para declarar
equivalência; os atributos servem para DETECTAR divergências e montar assinaturas reprodutíveis.
"""
import re

_NUM = r"(\d+(?:[.,]\d+)?)"


def _n(txt):
    t = txt.replace(",", ".")
    if t.count(".") > 1:                     # 1.000.000 -> milhar
        t = t.replace(".", "")
    try:
        v = float(t)
    except ValueError:
        return txt
    return ("%f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v))


# (nome do atributo, regex, função de canonização). A ordem importa só para a legibilidade.
PADROES = [
    ("formato_papel", re.compile(r"\b(A[0-6]|OFICIO|CARTA)\b(?=[ ,]|$)"), lambda m: m.group(1)),
    ("gramatura", re.compile(_NUM + r"\s*G\s*/\s*M\s*2\b"), lambda m: _n(m.group(1)) + " G/M2"),
    ("folhas", re.compile(_NUM + r"\s*(?:FOLHAS|FLS|FL)\b"), lambda m: _n(m.group(1)) + " FOLHAS"),
    ("concentracao_pct", re.compile(_NUM + r"\s*%"), lambda m: _n(m.group(1)) + "%"),
    ("concentracao_razao", re.compile(_NUM + r"\s*(MG|MCG|G|UI|MEQ)\s*/\s*" + r"(\d+(?:[.,]\d+)?)?\s*(ML|G|L|DOSE|GOTA)\b"),
     lambda m: f"{_n(m.group(1))} {m.group(2)}/{_n(m.group(3)) + ' ' if m.group(3) else ''}{m.group(4)}"),
    ("dosagem", re.compile(_NUM + r"\s*(MG|MCG|UI)\b(?!\s*/)"), lambda m: f"{_n(m.group(1))} {m.group(2)}"),
    ("volume", re.compile(_NUM + r"\s*(ML|L|LT|LITROS?|LITRO)\b(?!\s*/)"),
     lambda m: f"{_n(m.group(1))} {'ML' if m.group(2) == 'ML' else 'L'}"),
    ("peso", re.compile(_NUM + r"\s*(KG|G|GR|GRAMAS?|QUILOS?)\b(?!\s*/)"),
     lambda m: f"{_n(m.group(1))} {'KG' if m.group(2).startswith(('KG', 'QUILO')) else 'G'}"),
    ("dimensoes", re.compile(_NUM + r"\s*(?:MM|CM|M)?\s*X\s*" + _NUM + r"(?:\s*(?:MM|CM|M)?\s*X\s*" + _NUM + r")?\s*(MM|CM|M)?\b"),
     lambda m: "X".join(_n(g) for g in m.groups()[:3] if g) + (" " + m.group(4) if m.group(4) else "")),
    ("medida_linear", re.compile(_NUM + r"\s*(MM|CM|M|POL|POLEGADAS?)\b(?!\s*[X2/])"),
     lambda m: f"{_n(m.group(1))} {'POL' if m.group(2).startswith('POL') else m.group(2)}"),
    ("capacidade_eletrica", re.compile(_NUM + r"\s*(W|KW|V|VOLTS?|VA|KVA|A|AH|MAH|BTUS?|HZ)\b"),
     lambda m: f"{_n(m.group(1))} {m.group(2).rstrip('S') if m.group(2).startswith(('VOLT', 'BTU')) else m.group(2)}"),
    ("capacidade_dados", re.compile(_NUM + r"\s*(GB|TB|MB)\b"), lambda m: f"{_n(m.group(1))} {m.group(2)}"),
    ("unidades_por_embalagem", re.compile(
        r"\b(CAIXA|CX|PACOTE|PCT|EMBALAGEM|FRASCO|BLISTER|KIT|CARTELA|ROLO|FARDO|SACO|ESTOJO|CONJUNTO)\s*(?:COM|C/|C)\s*"
        + _NUM + r"\s*(UNIDADES?|UN|UND|PECAS?|FOLHAS|ROLOS|PARES|COMPRIMIDOS|ENVELOPES|SACOS)?\b"),
     lambda m: f"{m.group(1).replace('CX', 'CAIXA').replace('PCT', 'PACOTE')} {_n(m.group(2))}"),
    ("quantidade_unidades", re.compile(_NUM + r"\s*(UNIDADES|UNIDADE|UN|UND)\b"), lambda m: f"{_n(m.group(1))} UN"),
]

# Indicadores qualitativos (presença), não numéricos
INDICADORES = {
    "marca_modelo": re.compile(r"\b(MARCA|MODELO|REF\.?|REFERENCIA|PART ?NUMBER|P/N|CODIGO DO FABRICANTE|ORIGINAL)\b"),
    "aplicacao_variavel": re.compile(r"\bAPLICACAO\b"),
    "generico": re.compile(r"\b(DIVERSOS|DIVERSAS|VARIADOS|CONFORME (?:EDITAL|TERMO|ANEXO|ESPECIFICACAO)|SOB DEMANDA|A DEFINIR)\b"),
    "compatibilidade": re.compile(r"\b(COMPATIVEL|COMPATIBILIDADE)\b"),
    "certificacao": re.compile(r"\b(INMETRO|ANVISA|ABNT|NBR|ISO|CERTIFICAD[OA]|REGISTRO NO MS)\b"),
}


def extrair(texto_norm):
    """{atributo: tupla ordenada de valores canônicos} para o texto normalizado."""
    if not texto_norm:
        return {}
    out = {}
    usados = []
    for nome, rx, canon in PADROES:
        vals = set()
        for m in rx.finditer(texto_norm):
            # evita contar o mesmo trecho em dois atributos (ex.: '10 X 20 MM' não vira medida_linear)
            if any(a <= m.start() < b for a, b in usados):
                continue
            vals.add(canon(m))
            usados.append((m.start(), m.end()))
        if vals:
            out[nome] = tuple(sorted(vals))
    return out


def indicadores(texto_norm):
    if not texto_norm:
        return {}
    return {k: True for k, rx in INDICADORES.items() if rx.search(texto_norm)}


def assinatura(attrs):
    """Representação canônica e determinística dos atributos numéricos/objetivos."""
    if not attrs:
        return ""
    return "; ".join(f"{k}={'|'.join(v)}" for k, v in sorted(attrs.items()))


def segmentos(texto_norm, nome_pdm_norm=None):
    """Segmentos 'ATRIBUTO VALOR' do padrão descritivo do catálogo (separados por vírgula), sem o
    nome do PDM. Mede a especificidade da descrição."""
    if not texto_norm:
        return []
    partes = [p.strip() for p in texto_norm.split(",") if p.strip()]
    if partes and nome_pdm_norm and partes[0] == nome_pdm_norm:
        partes = partes[1:]
    elif partes and nome_pdm_norm is None:
        partes = partes[1:]
    return partes


def embalagem_divergente(attrs, unidade_norm, conteudo):
    """True se a descrição declara unidades por embalagem e a unidade de fornecimento contradiz:
    ex.: descrição 'CAIXA COM 12' com unidade 'CAIXA 50 UNIDADE'. 'UNIDADE' com 'CAIXA COM 12' é
    tratado como indício (não prova) de embalagem distinta."""
    emb = attrs.get("unidades_por_embalagem")
    if not emb:
        return False
    qts = {e.split(" ")[-1] for e in emb}
    if conteudo is not None:
        return conteudo not in qts
    return unidade_norm in ("UNIDADE",)
