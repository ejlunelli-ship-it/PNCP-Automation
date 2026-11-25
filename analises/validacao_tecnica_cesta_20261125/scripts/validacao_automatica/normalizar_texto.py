"""Normalização (reutiliza as regras 1.2.0 de scripts/normalizar_especificacoes.py, com seus testes de regressão)
e comparações textuais ancoradas no texto OFICIAL.

Regras novas (versão automática 2.0.0), todas inequívocas e testadas:
  * `contem(valor, texto)`: o valor oficial (chave compacta, que preserva '/', '.', '%' e separadores entre números)
    aparece no texto. Assim '1/2' NUNCA casa com '12', e '0.5' nunca casa com '5'.
  * `contem_tolerante`: além disso, aceita um espaço DENTRO de um número oficial ('5 0' por '50'), artefato de quebra
    de linha da fonte. Só vale quando o valor oficial tem o número contíguo; o uso é registrado como correção
    tipográfica e rebaixa a família para S2.
  * `igual_ao_oficial`: o texto da variante é o texto oficial a menos de espaços e pontuação, com os grupos de dígitos
    da variante obtidos só por PARTIÇÃO dos grupos oficiais (nunca por fusão: '7, 28' ≠ '72, 8').
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normalizar_especificacoes import chave_compacta, normalizar, sem_acentos  # noqa: E402,F401

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def texto_seguro(t, limite=None):
    """Texto externo não confiável: remove caracteres de controle; nunca é interpretado como instrução ou código."""
    t = _CTRL.sub(" ", t or "")
    return t[:limite] if limite else t


def compacto(t):
    return chave_compacta(normalizar(t))


def estrito(t):
    return re.sub(r"[^A-Z0-9]", "", compacto(t))


def contem(valor, texto_c):
    v = compacto(valor)
    return bool(v) and v in texto_c


def _padrao_tolerante(vc):
    partes = []
    for i, ch in enumerate(vc):
        partes.append(re.escape(ch))
        if ch.isdigit() and i + 1 < len(vc) and vc[i + 1].isdigit():
            partes.append(r"\|?")
    return re.compile("".join(partes))


def contem_tolerante(valor, texto_c):
    """(achou, usou_tolerancia)."""
    v = compacto(valor)
    if not v:
        return False, False
    if v in texto_c:
        return True, False
    achou = any(c.isdigit() for c in v) and bool(_padrao_tolerante(v).search(texto_c))
    return achou, achou


def igual_ao_oficial(variante, oficial):
    """(igual, tipo) com tipo em {'identico', 'espacamento', 'numero_quebrado'}; (False, None) se diferente.
    Só ESPAÇOS podem diferir: toda pontuação (inclusive '/', '.', ',' entre números) precisa coincidir, de modo que
    '1 2' ≠ '1/2' e '72, 8' ≠ '7, 28'. Se o espaço removido estava dentro de um número oficial, o tipo é
    'numero_quebrado' (correção tipográfica registrada)."""
    nv, no = normalizar(variante), normalizar(oficial)
    if nv == no:
        return True, "identico"
    if re.sub(r"\s+", "", nv) != re.sub(r"\s+", "", no):
        return False, None
    gv, go = re.findall(r"\d+", nv), re.findall(r"\d+", no)
    return True, ("espacamento" if gv == go else "numero_quebrado")
