"""Suficiência das evidências: perfis de atributos críticos por categoria, unidade de fornecimento × PDM oficial e
ressalvas que separam S1 (alta segurança) de S2 (segurança intermediária)."""
from .normalizar_texto import compacto, normalizar


def perfis_do_produto(requer_especialista):
    """Perfis aplicáveis. Regra de aplicabilidade (2.0.0): quando o produto é MEDICAMENTO, o perfil específico de
    medicamento substitui o de material médico (a cautela 'medicamentos_materiais_medicos' da cesta marca os dois;
    'material ou tipo' não é atributo crítico de um fármaco)."""
    riscos = [r for r in (requer_especialista or "").split(";") if r]
    if "medicamento" in riscos:
        riscos = [r for r in riscos if r != "material_medico"]
    return riscos or ["geral"]


def avaliar_perfis(canon, riscos, cfg_perfis, unidade_apresentacao=None):
    """Devolve (faltas, atendidos). Cada grupo crítico precisa de uma característica oficial (pelo nome) ou de um
    atributo tipado extraído das características oficiais. 'geral' exige um mínimo de características oficiais.
    Medicamento: o PDM (princípio ativo) conta no mínimo geral e `unidade_apresentacao` (unidade de fornecimento
    reconhecida no PDM oficial e da lista de apresentações) satisfaz 'forma ou apresentação'."""
    faltas, atendidos = [], []
    nomes = [compacto(c["nome"]) for c in canon["caracteristicas"] if c["valor_compacto"]]
    tip = set(canon["atributos_tipados"])
    n_ok = len(nomes) + (1 if "medicamento" in riscos and canon.get("tipo") else 0)
    minimo = cfg_perfis["geral"]["minimo_caracteristicas_oficiais"]
    if n_ok < minimo:
        faltas.append(f"geral: {n_ok} característica(s) oficial(is) com valor (mínimo {minimo})")
    for r in riscos:
        p = cfg_perfis.get(r)
        if not p or r == "geral":
            continue
        for grupo, regra in p.items():
            if grupo.startswith("_") or not isinstance(regra, dict):
                continue
            por_nome = [n for n in nomes if any(compacto(t) in n for t in regra["nomes"])]
            por_tipo = [a for a in tip if any(a.startswith(t) for t in regra["tipados"])]
            por_unidade = r == "medicamento" and grupo == "forma_ou_apresentacao" and bool(unidade_apresentacao)
            if por_nome or por_tipo or por_unidade:
                atendidos.append(f"{r}.{grupo}")
            else:
                faltas.append(f"{r}: falta {grupo.replace('_', ' ')} no catálogo oficial")
    return faltas, atendidos


def unidade_reconhecida(unidade_norm, parse, ficha, siglas):
    """(interpretavel, reconhecida_no_pdm, detalhe). parse vem da tabela `unidades` da cesta (embalagem, conteudo,
    unidade_conteudo, alerta)."""
    if not unidade_norm or not parse or parse.get("alerta"):
        return False, False, f"unidade não interpretável: {unidade_norm!r} {parse.get('alerta') if parse else ''}".strip()
    emb = normalizar(parse.get("embalagem") or unidade_norm)
    cont = parse.get("conteudo")
    uc = siglas.get(normalizar(parse.get("unidade_conteudo") or ""), normalizar(parse.get("unidade_conteudo") or ""))
    if ficha.get("status_unidades") != "OK":
        return True, False, "unidades oficiais do PDM indisponíveis"
    for u in ficha["unidades"]:
        nome = normalizar(u["nome"])
        if nome != emb and siglas.get(normalizar(u["sigla"]), "") != emb:
            continue
        if not cont:
            if not u["capacidade"] or float(u["capacidade"]) == 0:
                return True, True, f"unidade oficial {u['sigla']} ({u['nome']})" + ("" if u["ativo"] else " — inativa")
            continue
        try:
            igual_cap = abs(float(u["capacidade"]) - float(cont)) < 1e-9
        except (TypeError, ValueError):
            igual_cap = False
        um = siglas.get(normalizar(u["unidade_medida"]), normalizar(u["unidade_medida"]))
        if igual_cap and um == uc:
            return True, True, f"unidade oficial {u['sigla']} {u['capacidade']:g} {u['unidade_medida']}" + ("" if u["ativo"] else " — inativa")
    return True, False, f"unidade {unidade_norm} não consta das unidades oficiais do PDM"
