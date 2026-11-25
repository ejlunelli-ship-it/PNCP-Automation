"""Normalização conservadora das descrições.

Padroniza só a grafia: maiúsculas, acentos, espaços, pontuação irrelevante (':' e ';'), abreviações inequívocas,
grafias de unidade, separador decimal e símbolo de dimensão. NUNCA converte grandezas nem elimina números:
'0,5 L' vira '0.5 L' (e não '500 ML'); a equivalência numérica entre unidades é decidida só na extração de atributos,
dentro da mesma grandeza.
"""
import re
import unicodedata

VERSAO_NORMALIZACAO = "1.1.0"

_SUBST_CHAR = {"²": "2", "³": "3", "º": "O", "ª": "A", "°": " GRAUS ", "µ": "U", "μ": "U", "×": "X", "Ø": " DIAMETRO ",
               "ø": " DIAMETRO ", "“": '"', "”": '"', "″": '"', "’": "'", "‘": "'", "´": "'", "–": "-", "—": "-", " ": " "}

# unidades só são reescritas quando vêm IMEDIATAMENTE depois de um número (evita mexer em palavras do nome)
_UNIDADES = [
    (r"MILILITROS?|MLS", "ML"), (r"CENTILITROS?", "CL"), (r"LITROS?|LTS?|LT\.", "L"),
    (r"MICROGRAMAS?|MCGS?|UG", "MCG"), (r"MILIGRAMAS?|MGS", "MG"), (r"QUILOGRAMAS?|QUILOS?|KGS|KILOS?", "KG"),
    (r"GRAMAS?|GRS?|GRM", "G"),
    (r"MILIMETROS?", "MM"), (r"CENTIMETROS?|CMS", "CM"), (r"METROS?|MTS?", "M"), (r"POLEGADAS?|POL\.", "POL"),
    (r"WATTS?", "W"), (r"VOLTS?", "V"), (r"UNIDADES INTERNACIONAIS|U\.I\.", "UI"),
    (r"FLS?\.?|FOLHA", "FOLHAS"), (r"UNIDS?\.?|UNDS?\.?|UNS?\.?|UND", "UNIDADES"),
]
_RE_UNIDADES = [(re.compile(rf"(?<=\d) ?(?:{a})(?![A-Z0-9])"), f" {b}") for a, b in _UNIDADES]

# abreviações inequívocas (palavra inteira)
_ABREV = [
    (re.compile(r"\bC/\s*"), "COM "), (re.compile(r"\bS/\s*"), "SEM "), (re.compile(r"\bP/\s*"), "PARA "),
    # 'CX' NÃO é expandido: em 'TAMANHO (C X L)' / '(CX L)' significa comprimento × largura (regra 1.1.0)
    (re.compile(r"\bPCT\b\.?"), "PACOTE"), (re.compile(r"\bPCTS\b\.?"), "PACOTES"),
    (re.compile(r"\bAPROX\b\.?"), "APROXIMADAMENTE"), (re.compile(r"\bDIAM\b\.?"), "DIAMETRO"),
    (re.compile(r"\bLARG\b\.?"), "LARGURA"), (re.compile(r"\bCOMPR\b\.?"), "COMPRIMENTO"),
    (re.compile(r"\bQTDE?\b\.?"), "QUANTIDADE"), (re.compile(r"\bREF\b\.?(?=\s)"), "REFERENCIA"),
]

# 1.000 / 12.500.000 (pt-BR). Vírgula seguida de espaço é separador de lista, não decimal: '1:100.000, APRESENTAÇÃO'
# também é milhar (regra 1.1.0). '1.000,5' (milhar + vírgula decimal) -> '1000.5'.
_RE_MILHAR = re.compile(r"(?<![\d.])(?<!\d,)(\d{1,3})((?:\.\d{3})+)(?![\d.])(?!,\d)")
_RE_MILHAR_DEC = re.compile(r"(?<![\d.])(?<!\d,)(\d{1,3})((?:\.\d{3})+),(?=\d)")
_RE_DECIMAL = re.compile(r"(?<=\d),(?=\d)")
_RE_DIM = re.compile(r"(?<=\d)\s*[X*]\s*(?=\d)")
_RE_NUM_LETRA = re.compile(r"(?<=\d)(?=[A-Z%])")
_RE_POL_ASPAS = re.compile(r'(?<=\d)\s*(?:"|\'\')')
_RE_GM2 = re.compile(r"\bG(?:R|RAMAS?)?\s*/\s*M\s*2\b|\bGSM\b")
_RE_ESPACOS = re.compile(r"\s+")


def sem_acentos(texto):
    t = "".join(_SUBST_CHAR.get(c, c) for c in texto)
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def normalizar(texto, manter_dois_pontos=False):
    """Texto original -> texto normalizado (determinístico, sem perda de números ou unidades).
    `manter_dois_pontos` só serve para aprender as chaves 'ATRIBUTO:' do catálogo."""
    if texto is None:
        return ""
    t = sem_acentos(str(texto)).upper()
    t = _RE_POL_ASPAS.sub(" POL ", t)
    t = _RE_MILHAR_DEC.sub(lambda m: m.group(1) + m.group(2).replace(".", "") + ",", t)
    t = _RE_MILHAR.sub(lambda m: m.group(1) + m.group(2).replace(".", ""), t)
    t = _RE_DECIMAL.sub(".", t)
    t = _RE_DIM.sub(" X ", t)
    t = t.replace(";", ",")
    t = re.sub(r"\s*:\s*", ": ", t) if manter_dois_pontos else t.replace(":", " ")
    t = _RE_ESPACOS.sub(" ", t)
    t = _RE_NUM_LETRA.sub(" ", t)                  # 500ML -> 500 ML ; 70% -> 70 %
    t = re.sub(r"(?<=\d) %", "%", t)               # mas a porcentagem fica colada: 70%
    for rx, sub in _ABREV:
        t = rx.sub(sub, t)
    for rx, sub in _RE_UNIDADES:
        t = rx.sub(sub, t)
    t = _RE_GM2.sub("G/M2", t)
    t = re.sub(r"\b(MG|MCG|G|UI)\s*/\s*(ML|L|G|KG|100 ?ML)\b", lambda m: f"{m.group(1)}/{m.group(2).replace(' ', '')}", t)
    t = re.sub(r"\s*,\s*", ", ", t)
    t = re.sub(r"(,\s*)+", ", ", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = _RE_ESPACOS.sub(" ", t).strip(" ,.-")
    return t


def chave_compacta(normalizada):
    """Chave para detectar diferenças só de espaçamento/pontuação. Entre dígitos de grupos distintos fica '|',
    para que '7, 28' e '72, 8' NÃO colidam."""
    t = re.sub(r"(?<=\d)[^A-Z0-9.%/]+(?=\d)", "|", normalizada)
    return re.sub(r"[^A-Z0-9.%/|]", "", t)


def numeros(texto):
    """Sequências numéricas (ponto decimal) presentes no texto normalizado."""
    return re.findall(r"\d+(?:\.\d+)?", texto)
