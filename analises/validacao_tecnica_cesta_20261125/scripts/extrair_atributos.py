"""Extração determinística de atributos técnicos do texto normalizado.

Cada atributo devolve um conjunto de valores CANÔNICOS (com conversão só dentro da mesma grandeza e por fator exato)
e o trecho de origem. Grandezas diferentes ficam em atributos diferentes: massa ≠ dosagem ≠ concentração ≠ volume ≠
quantidade por embalagem ≠ gramatura. A extração só produz evidências; nunca aprova nada.

Duas famílias de atributos:
  * tipados (regras de config/regras_atributos.json): volume, massa, dosagem, concentração, gramatura, dimensões...
  * declarados: pares 'ATRIBUTO VALOR' do texto do catálogo (CATMAT/PDM), com o vocabulário de chaves aprendido das
    descrições que trazem 'ATRIBUTO: VALOR'. Os valores são comparados pela chave compacta (sem espaços/pontuação).
"""
import re
from collections import Counter
from decimal import Decimal

from normalizar_especificacoes import chave_compacta, normalizar

VERSAO_EXTRACAO = "1.2.0"
NUM = r"(\d+(?:\.\d+)?)"


def _fmt_num(x):
    """Número canônico: Decimal sem zeros à direita (evita 499.99999 por ponto flutuante); frações (1/2.7 POL)
    são arredondadas em 6 casas decimais, de forma determinística."""
    d = Decimal(str(x))
    if d.as_tuple().exponent < -6:
        d = d.quantize(Decimal("0.000001"))
    d = d.normalize()
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def _conv(valor, unidade, tabela):
    f = tabela["fatores"].get(unidade)
    if f is None:
        return None
    return f"{_fmt_num(Decimal(valor) * Decimal(str(f)))} {tabela['base']}"


def _alt(palavras):
    """Alternância regex, mais longas primeiro (casamento guloso determinístico)."""
    return "|".join(re.escape(p) for p in sorted(set(palavras), key=lambda s: (-len(s), s)))


class Extrator:
    def __init__(self, regras):
        self.r = regras
        cv = regras["conversoes"]
        self.cv = cv
        rot = regras["rotulos_dimensao"]
        qual = _alt(regras["qualificadores_medida"])
        self.rx_rotulo = {
            k: (re.compile(rf"\b(?:{_alt(v)})\b(?:\s+(?:{qual})\b)*\s*{NUM}\s*(MM|CM|M|POL)\b(?![/2-3])"),
                re.compile(rf"{NUM}\s*(MM|CM|M|POL)\s+(?:DE\s+)?(?:{_alt(v)})\b"))
            for k, v in rot.items()}
        # frações de polegada: '1/2 POL', '1 1/2 POL', '1/2.7 POL' (regra 1.1.0: antes '1/2 POL' virava '2 POL')
        self.rx_fracao = re.compile(r"(?<![\d./])(?:(\d+)\s+)?(\d+)/(\d+(?:\.\d+)?)\s*POL\b")
        self.rx_rotulo_antes = {k: re.compile(rf"\b(?:{_alt(v)})\b(?:\s+(?:{qual})\b)*\s*$") for k, v in rot.items()}
        self.generaliza_ff = {k: v for k, v in regras.get("generalizacoes_forma_farmaceutica", {}).items() if not k.startswith("_")}
        self.cfg_descolar = regras.get("descolar_chaves", {})
        self.rx_descolar = None
        self.rx_conc_pct = re.compile(rf"{NUM}%")
        self.rx_conc_outras = re.compile(rf"{NUM}\s*(MEQ|MMOL|MOL|UI|U|MCG|MG|G)\s*/\s*(ML|L|DOSE|JATO|GOTA|G|KG|ACIONAMENTO|PUFF)\b")
        self.rx_unid_dose = re.compile(rf"{NUM}\s*(U|UI|MEQ|MMOL)\b(?!\s*/)")
        self.rx_conc_por_vol = re.compile(rf"{NUM}\s*(MCG|MG|G)\s*/\s*{NUM}\s*ML\b")
        self.rx_conc = re.compile(rf"{NUM}\s*(MCG|MG|G|UI)\s*/\s*(ML|L|G|KG|100ML)\b")
        self.rx_gram = re.compile(rf"{NUM}\s*G/M2\b")
        self.rx_gram_sem_un = re.compile(rf"\bGRAMATURA\b(?:\s+(?:{qual})\b)*\s*{NUM}\b(?!\s*(?:G/M2|%|[A-Z]))")
        self.rx_capac = re.compile(rf"\bCAPACIDADE\b(?:\s+(?:{qual}|ARMAZENAMENTO|NOMINAL|VOLUMETRICA)\b)*\s*{NUM}\s*"
                                   r"(ML|CL|L|M3|CC|CM3|MCG|MG|G|KG|MB|GB|TB|FOLHAS|BTUS?|PESSOAS|LUGARES)\b")
        self.rx_pot = re.compile(rf"{NUM}\s*(KW|W)\b")
        self.rx_pot_cv = re.compile(rf"{NUM}\s*(CV|HP)\b")
        self.rx_tensao2 = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*V\b")
        self.rx_tensao = re.compile(r"\b(\d{1,4}(?:\.\d+)?)\s*(V|VCC|VCA|VAC|VDC)\b")
        self.rx_bivolt = re.compile(r"\bBIVOLT\b")
        self.rx_dim = re.compile(rf"{NUM}\s*(MM|CM|M|POL)?\s*X\s*{NUM}\s*(MM|CM|M|POL)?(?:\s*X\s*{NUM})?\s*(MM|CM|M|POL)?\b")
        fp = _alt(regras["formatos_papel"])
        self.rx_papel = re.compile(rf"\b(?:FORMATO|TAMANHO|PAPEL|FOLHA|FOLHAS)\b[^,]{{0,30}}?\b({fp})\b")
        self.rx_folhas = re.compile(r"\b(\d+)\s*FOLHAS\b")
        emb = _alt(regras["embalagens"])
        cont = _alt([u for u in regras["unidades_contaveis"] if not u.startswith("FOLHA")])
        self.rx_qtd_emb = re.compile(rf"\b(?:{emb})S?\b\s+(?:COM\s+|CONTENDO\s+|DE\s+|C\s+)?(\d+)\s*({cont})\b")
        self.rx_qtd_com = re.compile(rf"\b(?:COM|CONTENDO)\s+(\d+)\s*({cont})\b")
        self.rx_unid = re.compile(rf"\b(\d+)\s*({cont})\b")
        self.rx_massa_rot = re.compile(rf"\b(?:PESO|MASSA|PESO LIQUIDO|PESO BRUTO)\b(?:\s+(?:{qual}|LIQUIDO|BRUTO)\b)*\s*{NUM}\s*(MCG|MG|G|KG)\b")
        self.rx_massa = re.compile(rf"{NUM}\s*(MCG|MG|G|KG)\b(?!\s*/)")
        self.rx_ui = re.compile(rf"{NUM}\s*UI\b(?!\s*/)")
        self.rx_vol = re.compile(rf"{NUM}\s*(ML|CL|DL|L|M3|CC|CM3)\b(?!\s*/)")
        self.rx_lin = re.compile(rf"{NUM}\s*(MM|CM|M|POL)\b(?![/2-3])")
        self.rx_tipo_num = re.compile(r"\bTIPO\s+(\d{1,2}|I{1,3}|IV|V)\b")
        self.rx_classe = re.compile(r"\bCLASSE\s+([A-Z0-9]{1,3})\b")
        self.rx_grau = re.compile(r"\bGRAU\s+(ALIMENTICIO|TECNICO|FARMACEUTICO|USP|PA|ANALITICO|REAGENTE|INDUSTRIAL|HOSPITALAR|CIRURGICO|MEDICINAL)\b")
        self.rx_nbr = re.compile(r"\bNBR\s*(?:ISO\s*)?(\d{3,6}(?:-\d+)?)")
        self.rx_iso = re.compile(r"\bISO\s*(\d{3,6})")
        self.rx_ca = re.compile(r"\bC\.?A\.?\s*(?:N\.?O?\s*)?(\d{4,6})\b")
        self.rx_compat = re.compile(r"\bCOMPATIVEL\s+(?:COM|PARA)\s+([^,]+)")
        self.rx_para_eq = re.compile(r"\bPARA\s+(?:USO\s+EM\s+)?(?:IMPRESSORAS?|EQUIPAMENTOS?|VEICULOS?|APARELHOS?|MAQUINAS?|MULTIFUNCIONAIS?)\s+([^,]+)")
        self.rx_modelo = re.compile(r"\bMODELO\s+([^,]+)")
        self.rx_pn = re.compile(r"\b(?:PART NUMBER|P/N|PN)\s*([A-Z0-9][A-Z0-9\-\.]{2,})")
        self.rx_ref = re.compile(r"\bREFERENCIA\s+([^,]+)")
        self.rx_tipo_emb = re.compile(rf"\b(?:EMBALAGEM|EMBALAGENS|ACONDICIONAD[OA]S?|EMBALAD[OA]S?)\b(?:\s+(?:EM|TIPO|COM|DE|INDIVIDUAL|ORIGINAL|PRIMARIA|SECUNDARIA))*\s+({emb})\b")
        self.rx_composicao = re.compile(r"\bCOMPOSICAO\s+([^,]+)")
        self.rx_comp_pct = re.compile(r"\b(\d+)%\s*(ALGODAO|POLIESTER|VISCOSE|ELASTANO|NYLON|POLIAMIDA|LA|LINHO|ACRILICO|SEDA|POLIPROPILENO)\b")
        self.rx_cor_seg = re.compile(r"\bCOR(?:ES)?\b")

        def vocab(d):
            pares = [(s, k) for k, ss in d.items() if not k.startswith("_") for s in ss]
            alt = _alt([s for s, _ in pares])
            return re.compile(rf"(?<![A-Z0-9])(?:{alt})(?![A-Z0-9])"), {s: k for s, k in pares}
        self.v_cor = vocab(regras["cores"])
        self.v_mat = vocab(regras["materiais"])
        self.mat_contexto = {"LA", "PET", "EVA", "ABS", "PAPEL", "VIDRO", "CELULOSE", "CERAMICA"}
        self.v_ff = vocab(regras["formas_farmaceuticas"])
        self.v_est = vocab(regras["esterilidade"])
        self.v_uso = vocab(regras["tipos_uso"])
        self.v_orig = vocab(regras["originalidade"])
        self.v_qual = vocab(regras["qualidade"])
        self.v_cert = vocab(regras["certificacoes"])
        self.rx_notas = re.compile(rf"(?<![A-Z0-9])(?:{_alt(regras['notas_catalogo'])})(?![A-Z0-9])")

    # ------------------------------------------------------------------------------------------------------
    def definir_chaves(self, chaves):
        """Vocabulário de chaves declaradas usado para descolar 'CHAVEVALOR' antes da extração tipada (regra 1.1.0)."""
        c = self.cfg_descolar
        if not c:
            return
        nunca = c.get("nunca_antes_de", {})
        sel = sorted({k for k in chaves if len(re.sub(r"[^A-Z]", "", k)) >= c.get("min_letras", 7)} | set(c.get("sempre", [])),
                     key=lambda k: (-len(k), k))
        pats = []
        for k in sel:
            corpo = r"\s*".join(re.escape(p) for p in k.split())
            neg = "".join(f"(?!{re.escape(x)})" for x in nunca.get(k, []))
            pats.append(f"{corpo}{neg}")
        self.rx_descolar = re.compile(rf"(?<![A-Z0-9])(?:{'|'.join(pats)})(?=[A-Z0-9])") if pats else None

    def extrair(self, t, contexto=None):
        """t: texto normalizado. contexto: {'medicamento': bool, 'originalidade': bool}.
        Devolve {atributo: {valor_canonico: [trechos]}}."""
        ctx = contexto or {}
        if self.rx_descolar is not None:
            t = self.rx_descolar.sub(lambda m: m.group(0) + " ", t)
        out = {}
        usado = [False] * len(t)

        def livre(a, b):
            return not any(usado[a:b])

        def marca(a, b):
            for i in range(a, b):
                usado[i] = True

        def add(attr, val, trecho):
            out.setdefault(attr, {}).setdefault(val, [])
            if trecho not in out[attr][val]:
                out[attr][val].append(trecho)

        def varrer(rx, fn, consumir=True):
            for m in rx.finditer(t):
                if not livre(m.start(), m.end()):
                    continue
                res = fn(m)
                if res:
                    for attr, val in (res if isinstance(res, list) else [res]):
                        if val is not None:
                            add(attr, val, m.group(0))
                    if consumir:
                        marca(m.start(), m.end())

        cv = self.cv
        # 1. concentrações (antes de massa e volume, que também casariam '500 MG' de '500 MG/ML')
        def conc_vol(m):
            v = Decimal(m.group(1)) / Decimal(m.group(3))
            return ("concentracao_massa_volume", _conv(v, f"{m.group(2)}/ML", cv["concentracao_massa_volume"]))
        varrer(self.rx_conc_por_vol, conc_vol)

        def conc(m):
            un = f"{m.group(2)}/{m.group(3)}"
            if m.group(2) == "UI":
                return ("concentracao_ui_volume", _conv(m.group(1), un, cv["concentracao_ui_volume"])
                        if m.group(3) == "ML" else f"{_fmt_num(m.group(1))} {un}")
            tab = cv["concentracao_massa_massa"] if m.group(3) in ("G", "KG") else cv["concentracao_massa_volume"]
            nome = "concentracao_massa_massa" if m.group(3) in ("G", "KG") else "concentracao_massa_volume"
            return (nome, _conv(m.group(1), un, tab))
        varrer(self.rx_conc, conc)
        # outras concentrações sem conversão entre si: MEQ/ML, MMOL/L, U/ML, MCG/DOSE, MG/GOTA... (regra 1.2.0)
        varrer(self.rx_conc_outras, lambda m: ("concentracao_outras", f"{_fmt_num(m.group(1))} {m.group(2)}/{m.group(3)}"))
        varrer(self.rx_conc_pct, lambda m: ("concentracao_pct", f"{_fmt_num(m.group(1))}%"))
        # 2. gramatura
        varrer(self.rx_gram, lambda m: ("gramatura", f"{_fmt_num(m.group(1))} G/M2"))
        varrer(self.rx_gram_sem_un, lambda m: ("gramatura", f"{_fmt_num(m.group(1))} (SEM UNIDADE)"))
        # 3. capacidade (por grandeza)
        def capac(m):
            v, u = m.group(1), m.group(2)
            if u in cv["volume"]["fatores"]:
                return ("capacidade_volume", _conv(v, u, cv["volume"]))
            if u in cv["massa"]["fatores"]:
                return ("capacidade_massa", _conv(v, u, cv["massa"]))
            if u in cv["dados"]["fatores"]:
                return ("capacidade_dados", _conv(v, u, cv["dados"]))
            return ("capacidade_" + {"FOLHAS": "folhas", "BTU": "btu", "BTUS": "btu"}.get(u, "pessoas"), f"{_fmt_num(v)} {u.rstrip('S') if u.startswith('BTU') else u}")
        varrer(self.rx_capac, capac)
        # 3b. frações de polegada (com o rótulo que as precede, se houver)
        def fracao(m):
            v = Decimal(m.group(1) or 0) + Decimal(m.group(2)) / Decimal(m.group(3))
            antes = t[max(0, m.start() - 40):m.start()]
            nome = next((k for k, rx in self.rx_rotulo_antes.items() if rx.search(antes)), "medida_linear")
            return (nome, _conv(v, "POL", cv["comprimento"]))
        varrer(self.rx_fracao, fracao)
        # 4. dimensões rotuladas
        for nome, (rx1, rx2) in self.rx_rotulo.items():
            varrer(rx1, lambda m, n=nome: (n, _conv(m.group(1), m.group(2), cv["comprimento"])))
            varrer(rx2, lambda m, n=nome: (n, _conv(m.group(1), m.group(2), cv["comprimento"])))
        # 5. dimensões AxB(xC)
        def dim(m):
            nums = [m.group(1), m.group(3)] + ([m.group(5)] if m.group(5) else [])
            uns = [m.group(2), m.group(4), m.group(6)]
            un_final = uns[2] or uns[1] or uns[0]
            if un_final is None:
                return ("dimensoes", "X".join(_fmt_num(x) for x in nums) + " (SEM UNIDADE)")
            conv = []
            for i, x in enumerate(nums):
                u = uns[i] if i < 2 and uns[i] else un_final
                conv.append(_conv(x, u, cv["comprimento"]).split()[0])
            return ("dimensoes", "X".join(conv) + " MM")
        varrer(self.rx_dim, dim)
        # 6. elétrica
        varrer(self.rx_tensao2, lambda m: ("tensao", f"{m.group(1)}/{m.group(2)} V"))
        varrer(self.rx_bivolt, lambda m: ("tensao", "BIVOLT"))
        varrer(self.rx_tensao, lambda m: ("tensao", f"{_fmt_num(m.group(1))} {'V' if m.group(2) == 'V' else m.group(2)}"))
        varrer(self.rx_pot, lambda m: ("potencia", _conv(m.group(1), m.group(2), cv["potencia"])))
        varrer(self.rx_pot_cv, lambda m: ("potencia", f"{_fmt_num(m.group(1))} {m.group(2)}"))
        # 7. papel, folhas, quantidades
        varrer(self.rx_papel, lambda m: ("formato_papel", m.group(1)), consumir=False)
        varrer(self.rx_folhas, lambda m: ("numero_folhas", f"{int(m.group(1))} FOLHAS"))
        def qtd(m):
            u = m.group(2)
            u = "UNIDADES" if u in ("UNIDADE", "UNIDADES", "PECA", "PECAS") else ("PARES" if u in ("PAR", "PARES") else u)
            return ("quantidade_embalagem", f"{int(m.group(1))} {u}")
        varrer(self.rx_qtd_emb, qtd)
        varrer(self.rx_qtd_com, qtd)
        def unid(m):
            u = m.group(2)
            u = "UNIDADES" if u in ("UNIDADE", "UNIDADES", "PECA", "PECAS") else ("PARES" if u in ("PAR", "PARES") else u)
            return ("numero_unidades", f"{int(m.group(1))} {u}")
        varrer(self.rx_unid, unid)
        # 8. massa (dosagem em medicamento), UI, volume, comprimento sem rótulo
        varrer(self.rx_massa_rot, lambda m: ("massa", _conv(m.group(1), m.group(2), cv["massa"])))
        varrer(self.rx_massa, lambda m: ("dosagem" if ctx.get("medicamento") else "massa", _conv(m.group(1), m.group(2), cv["massa"])))
        varrer(self.rx_ui, lambda m: ("dosagem_ui", f"{_fmt_num(m.group(1))} UI"))
        if ctx.get("medicamento"):
            varrer(self.rx_unid_dose, lambda m: ("dosagem_" + m.group(2).lower(), f"{_fmt_num(m.group(1))} {m.group(2)}"))
        varrer(self.rx_vol, lambda m: ("volume", _conv(m.group(1), m.group(2), cv["volume"])))
        varrer(self.rx_lin, lambda m: ("medida_linear", _conv(m.group(1), m.group(2), cv["comprimento"])))

        # ---------------------------------------------------------------------------------------- categóricos
        segs = [s.strip() for s in t.split(",")]
        for s in segs:
            if self.rx_cor_seg.search(s):
                rx, mapa = self.v_cor
                for m in rx.finditer(s):
                    add("cor", mapa[m.group(0)], s)
        rx, mapa = self.v_mat
        ocupado = [False] * len(t)
        for m in rx.finditer(t):
            if any(ocupado[m.start():m.end()]):
                continue
            k = mapa[m.group(0)]
            if k in self.mat_contexto:
                seg = next((s for s in segs if m.group(0) in s), "")
                if not re.search(r"\b(?:MATERIAL|COMPOSICAO|CONFECCIONAD|FABRICAD|CORPO|EM)\b", seg):
                    continue
            add("material", k, m.group(0))
            for i in range(m.start(), m.end()):
                ocupado[i] = True
        if ctx.get("medicamento"):
            rx, mapa = self.v_ff
            for m in rx.finditer(t):
                ff = mapa[m.group(0)]
                add("forma_farmaceutica", ff, m.group(0))
                for g in self.generaliza_ff.get(ff, []):        # forma específica implica as genéricas (regra 1.1.0)
                    add("forma_farmaceutica", g, f"{m.group(0)} (implica {g})")
        rx, mapa = self.v_est
        ocup = [False] * len(t)
        for m in rx.finditer(t):
            if not any(ocup[m.start():m.end()]):
                add("esterilidade", mapa[m.group(0)], m.group(0))
                for i in range(m.start(), m.end()):
                    ocup[i] = True
        for nome, (rx, mapa) in (("tipo_uso", self.v_uso), ("classe_qualidade", self.v_qual), ("certificacao", self.v_cert)):
            for m in rx.finditer(t):
                add(nome, mapa[m.group(0)], m.group(0))
        for m in self.rx_tipo_num.finditer(t):
            add("classe_qualidade", f"TIPO {m.group(1)}", m.group(0))
        for m in self.rx_classe.finditer(t):
            add("classe_qualidade", f"CLASSE {m.group(1)}", m.group(0))
        for m in self.rx_grau.finditer(t):
            add("classe_qualidade", f"GRAU {m.group(1)}", m.group(0))
        for m in self.rx_nbr.finditer(t):
            add("norma_tecnica", f"NBR {m.group(1)}", m.group(0))
        for m in self.rx_iso.finditer(t):
            add("norma_tecnica", f"ISO {m.group(1)}", m.group(0))
        if ctx.get("originalidade"):
            rx, mapa = self.v_orig
            for m in rx.finditer(t):
                if mapa[m.group(0)] == "COMPATIVEL" and re.match(r"\s+(?:COM|PARA)\b", t[m.end():]):
                    continue
                add("originalidade", mapa[m.group(0)], m.group(0))
        for rx, nome in ((self.rx_compat, "compatibilidade"), (self.rx_para_eq, "compatibilidade"), (self.rx_modelo, "modelo"),
                         (self.rx_pn, "modelo"), (self.rx_ref, "referencia_tecnica"), (self.rx_composicao, "composicao")):
            for m in rx.finditer(t):
                add(nome, chave_compacta(m.group(1).strip()), m.group(0))
        for m in self.rx_comp_pct.finditer(t):
            add("composicao", f"{m.group(1)}% {m.group(2)}", m.group(0))
        for m in self.rx_tipo_emb.finditer(t):
            add("tipo_embalagem", m.group(1), m.group(0))
        return out

    def notas_catalogo(self, t):
        return sorted({m.group(0) for m in self.rx_notas.finditer(t)})


# ---------------------------------------------------------------------------------------------- atributos declarados
_RX_CHAVE = re.compile(r"(?:^|,)\s*([A-Z][A-Z0-9 ()/\-\.]*?)\s*:")


def chaves_com_dois_pontos(texto_original):
    """Chaves 'ATRIBUTO:' de uma descrição original (só para aprender o vocabulário)."""
    t = normalizar(texto_original, manter_dois_pontos=True)
    out = []
    for m in _RX_CHAVE.finditer(t):
        k = re.sub(r"\s+", " ", m.group(1)).strip(" .-")
        if k and "(" not in k and ")" not in k:
            out.append(k)
    return out


class Vocabulario:
    """Chaves de atributos declarados, aprendidas das descrições com 'ATRIBUTO: VALOR' (determinístico)."""

    def __init__(self, contagem, min_ocorrencias=3, max_palavras=5):
        self.globais = sorted({k for k, n in contagem.items() if n >= min_ocorrencias and len(k.split()) <= max_palavras},
                              key=lambda k: (-len(chave_compacta(k)), k))
        self.compactas = {k: chave_compacta(k) for k in self.globais}

    @classmethod
    def de_textos(cls, textos, min_ocorrencias=3, max_palavras=5):
        c = Counter()
        for tx in textos:
            for k in set(chaves_com_dois_pontos(tx)):
                c[k] += 1
        return cls(c, min_ocorrencias, max_palavras)

    def pares(self, normalizada, chaves_produto=()):
        """Texto normalizado (sem ':') -> (nome, [(chave, valor_compacto, valor_texto)]).
        As chaves do próprio produto têm prioridade; entre as candidatas vence a mais longa."""
        segs = [s.strip() for s in normalizada.split(",")]
        if not segs:
            return "", []
        prod = sorted(set(chaves_produto), key=lambda k: (-len(chave_compacta(k)), k))
        candidatas = prod + [k for k in self.globais if k not in set(prod)]
        nome, pares = segs[0], []
        for s in segs[1:]:
            cs = chave_compacta(s)
            achou = None
            for k in candidatas:
                ck = self.compactas.get(k) or chave_compacta(k)
                if ck and cs.startswith(ck) and len(cs) > len(ck):
                    achou = k
                    break
            if achou:
                ck = chave_compacta(achou)
                pares.append([achou, cs[len(ck):], s])
            elif pares:
                pares[-1][1] += "," + cs
                pares[-1][2] += ", " + s
            else:
                nome += ", " + s
        return nome, [tuple(p) for p in pares]
