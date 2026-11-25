"""Normalização conservadora de textos, códigos, datas e unidades de fornecimento.

Todas as funções são puras e preservam a possibilidade de recuperar o valor original (o original
é sempre gravado ao lado do normalizado). Nenhuma conversão física entre unidades é feita.
"""
import csv
import re
import unicodedata
from pathlib import Path

# ------------------------------------------------------------------------------------- texto

_PONTUACAO_IRRELEVANTE = re.compile(r"[;:!?\"'`´“”‘’()\[\]{}|_*#@]+")
_ESPACOS = re.compile(r"\s+")
_ESPACO_ANTES_VIRGULA = re.compile(r"\s+,")
# vírgula seguida de espaço, exceto o separador decimal entre dígitos ('1,00' permanece '1,00')
_VIRGULA_SEM_ESPACO = re.compile(r"(?<!\d),(?=\S)|,(?=[^\d\s])")
_VIRGULA_ESPACOS = re.compile(r",\s+")


def sem_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalizar_texto(s):
    """Maiúsculas, sem acento, sem pontuação irrelevante, espaços colapsados. Mantém vírgula,
    ponto, barra, hífen, %, sinais de unidade (², ³ viram 2, 3) e dígitos, que carregam atributos."""
    if s is None:
        return None
    s = str(s)
    s = s.replace("²", "2").replace("³", "3").replace("º", "O").replace("ª", "A").replace("µ", "U")
    s = sem_acentos(s).upper()
    s = _PONTUACAO_IRRELEVANTE.sub(" ", s)
    s = _ESPACO_ANTES_VIRGULA.sub(",", s)
    s = _VIRGULA_SEM_ESPACO.sub(", ", s)
    s = _VIRGULA_ESPACOS.sub(", ", s)
    s = _ESPACOS.sub(" ", s).strip(" ,.-")
    return s or None


def chave_textual(s):
    """Chave mais agressiva, usada só para agrupar variantes de formatação da MESMA descrição
    (ex.: 'MATERIAL: METAL ,' e 'MATERIAL METAL,'). Remove toda pontuação e espaços; mantém
    letras e dígitos na ordem. Não é usada para declarar equivalência material."""
    n = normalizar_texto(s)
    if n is None:
        return None
    n = re.sub(r"(?<=\d)[.,](?=\d)", "D", n)        # preserva separador decimal entre dígitos
    return re.sub(r"[^A-Z0-9D%]", "", n) or None


# ------------------------------------------------------------------------------------- códigos

def normalizar_catmat(v):
    """'445485', '445485.0', 445485, ' 445485 ' -> 445485. Inválido -> None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v > 0 else None
    if isinstance(v, float):
        return int(v) if v.is_integer() and v > 0 else None
    s = str(v).strip()
    m = re.fullmatch(r"0*(\d{1,9})(?:\.0+)?", s)
    if not m:
        return None
    n = int(m.group(1))
    return n if n > 0 else None


def normalizar_uasg(v):
    """UASG do Compras.gov.br: código numérico de até 6 dígitos, devolvido com 6 dígitos.
    Inválido (vazio, não numérico, zero, mais de 6 dígitos) -> None."""
    if v is None:
        return None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if not re.fullmatch(r"\d{1,6}", s) or int(s) == 0:
        return None
    return s.zfill(6)


def normalizar_cnpj(v):
    if v is None:
        return None
    s = re.sub(r"\D", "", str(v))
    return s.zfill(14) if 1 <= len(s) <= 14 and int(s) != 0 else None


# ------------------------------------------------------------------------------------- datas

_DATA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def normalizar_data(v, minimo="2000-01-01", maximo="2100-12-31"):
    """Texto ISO ('2024-05-03T10:00:00', '2024-05-03 00:00:00.0000000') -> 'AAAA-MM-DD'.
    Data impossível ou fora de [minimo, maximo] -> None."""
    if v is None:
        return None
    m = _DATA.match(str(v).strip())
    if not m:
        return None
    a, me, d = (int(x) for x in m.groups())
    if not (1 <= me <= 12):
        return None
    dias = [31, 29 if (a % 4 == 0 and (a % 100 != 0 or a % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if not (1 <= d <= dias[me - 1]):
        return None
    s = f"{a:04d}-{me:02d}-{d:02d}"
    return s if minimo <= s <= maximo else None


def trimestre(data_iso):
    if not data_iso:
        return None
    return f"{data_iso[:4]}T{(int(data_iso[5:7]) - 1) // 3 + 1}"


# ------------------------------------------------------------------------------------- unidades

_UN_EMBALAGEM = re.compile(r"^(?P<emb>[A-Z][A-Z /\-]*?)\s+(?P<qtd>\d+(?:[.,]\d+)?)\s+(?P<un>[A-Z][A-Z0-9 /\-]*)$")
_UN_SO_QTD = re.compile(r"^(?P<emb>[A-Z][A-Z /\-]*?)\s+(?P<qtd>\d+(?:[.,]\d+)?)$")
_UN_SIMPLES = re.compile(r"^[A-Z][A-Z0-9 /\-]*$")


def _numero_canonico(txt):
    """'50,00' -> '50'; '3,60' -> '3.6'; '0,50' -> '0.5'. Só formatação, sem arredondar."""
    t = txt.replace(".", "").replace(",", ".") if ("," in txt) else txt
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    t = t.lstrip("0") or "0"
    if t.startswith("."):
        t = "0" + t
    return t


def carregar_aliases(caminho):
    """Tabela explícita de aliases de unidade: coluna `forma` (já normalizada por normalizar_texto),
    `canonica` e `fundir` (sim/nao). Só linhas com fundir=sim são aplicadas."""
    aliases = {}
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["fundir"].strip().lower() == "sim":
                aliases[r["forma"].strip()] = r["canonica"].strip()
    return aliases


def normalizar_unidade(original, aliases):
    """Devolve dict com a unidade normalizada e seus componentes:
    - `unidade_norm`: forma canônica (base da família CATMAT × unidade);
    - `embalagem`, `conteudo`, `unidade_conteudo`: quando a unidade é 'Caixa 50,00 UN' etc.;
    - `alerta`: vazio, 'unidade_ausente', 'conteudo_zero', 'formato_nao_reconhecido'.
    Nenhuma conversão física: 'CAIXA 50 UN' e 'UNIDADE' continuam diferentes; '1000 ML' ≠ '1 L'."""
    n = normalizar_texto(original)
    if not n:
        return {"unidade_norm": None, "embalagem": None, "conteudo": None, "unidade_conteudo": None,
                "alerta": "unidade_ausente"}
    m = _UN_EMBALAGEM.match(n)
    if m:
        emb = aliases.get(m.group("emb").strip(), m.group("emb").strip())
        qtd = _numero_canonico(m.group("qtd"))
        un = aliases.get(m.group("un").strip(), m.group("un").strip())
        alerta = "conteudo_zero" if float(qtd) == 0 else ""
        return {"unidade_norm": f"{emb} {qtd} {un}", "embalagem": emb, "conteudo": qtd,
                "unidade_conteudo": un, "alerta": alerta}
    m = _UN_SO_QTD.match(n)
    if m:
        # 'UNIDADE 0,00', 'QUILOGRAMA 0,00': quantidade sem unidade de conteúdo (cadastro antigo).
        emb = aliases.get(m.group("emb").strip(), m.group("emb").strip())
        qtd = _numero_canonico(m.group("qtd"))
        return {"unidade_norm": f"{emb} {qtd}", "embalagem": emb, "conteudo": qtd, "unidade_conteudo": None,
                "alerta": "conteudo_zero" if float(qtd) == 0 else "conteudo_sem_unidade"}
    if _UN_SIMPLES.match(n):
        u = aliases.get(n, n)
        return {"unidade_norm": u, "embalagem": u, "conteudo": None, "unidade_conteudo": None, "alerta": ""}
    return {"unidade_norm": n, "embalagem": None, "conteudo": None, "unidade_conteudo": None,
            "alerta": "formato_nao_reconhecido"}


def aliases_padrao():
    return carregar_aliases(Path(__file__).resolve().parents[1] / "config" / "aliases_unidades.csv")
