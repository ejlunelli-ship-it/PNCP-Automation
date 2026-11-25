"""Etapa 3: regimes trimestrais inequívocos e eventos de troca de modo (somente modos; nenhum preço).

Evento e = (u, t0): a UASG u está em regime inequívoco o em t0−1 e em regime inequívoco d ≠ o em t0 (t0 = 1º
trimestre completo observado no novo regime). Elegibilidade inicial NÃO depende do que acontece depois de t0; a
persistência (t0+1) é só classificada e usada numa sensibilidade explicitamente selecionada por trajetória.
"""
import numpy as np
import pandas as pd

from . import comum
from .construir_painel import A, AF, MISTO, NAO_OBS

ROT = {A: "A", AF: "AF", MISTO: "misto", NAO_OBS: "sem_compras"}


def eventos(status, t_ini, unidades, cnpj, formacao_ini=-6, falsif_fim=-2):
    """status: U × T (A, AF, MISTO, NAO_OBS). Retorna DataFrame de todos os eventos inequívocos."""
    U, T = status.shape
    linhas = []
    for i in range(U):
        s = status[i]
        ev_u = []
        for j in range(1, T):
            o, d = s[j - 1], s[j]
            if o in (A, AF) and d in (A, AF) and o != d:
                ev_u.append(j)
        for k, j in enumerate(ev_u):
            o, d = int(s[j - 1]), int(s[j])
            hist = [s[jj] if jj >= 0 else NAO_OBS for jj in range(j + formacao_ini, j + falsif_fim + 1)]
            compat = all(h in (o, NAO_OBS) for h in hist)
            if j + 1 >= T:
                pers = "fora_dos_dados"
            else:
                pers = {d: "persistente", o: "revertida", MISTO: "misto_em_t0+1", NAO_OBS: "sem_compras_em_t0+1"}[int(s[j + 1])]
            outros = [jj for jj in ev_u if jj != j and j + formacao_ini <= jj <= j + 1]
            linhas.append({"uasg": unidades[i], "u": i, "cnpj": cnpj[i], "t0": t_ini + j, "t0_nome": comum.nome_tri(t_ini + j),
                           "origem": ROT[o], "destino": ROT[d], "direcao": "A->AF" if o == A else "AF->A",
                           "sinal_af": 1 if o == A else -1, "episodio": k + 1, "eventos_na_uasg": len(ev_u),
                           "historico_modo_compativel": bool(compat),
                           "historico_modos": "|".join(ROT[int(h)] for h in hist),
                           "persistencia_t0+1": pers, "outro_evento_na_janela": bool(outros)})
    return pd.DataFrame(linhas)


def perdas_por_misto(status, frac, t_ini):
    """Trocas que existiriam pela regra de maioria (fração AF ≥ 0,5) entre trimestres observados consecutivos mas
    que envolvem um trimestre misto em t0−1 ou t0 (não classificadas na análise principal)."""
    U, T = status.shape
    n = 0
    por_t = {}
    for i in range(U):
        for j in range(1, T):
            a, b = status[i, j - 1], status[i, j]
            if a == NAO_OBS or b == NAO_OBS:
                continue
            Da, Db = frac[i, j - 1] >= 0.5, frac[i, j] >= 0.5
            if Da != Db and (a == MISTO or b == MISTO):
                n += 1
                por_t[t_ini + j] = por_t.get(t_ini + j, 0) + 1
    return n, por_t


def regra_anterior(c, P, ev):
    """Reproduz a classificação do estudo anterior (painel 2023T1–2026T1, fração AF ≥ 0,5, persistência 2) a partir
    do eventos_info.pkl da rodada S1 e compara com os eventos inequívocos."""
    E = pd.read_pickle(comum.resolver(c["fontes"]["dados_S1"]) / "eventos_info.pkl")
    info, ti = E["info"], E["tri_ini"]
    tr = info[info.tipo == "troca"].copy()
    tr["t0"] = ti + tr.F.astype(int)
    chave_nova = set(zip(ev.uasg, ev.t0))
    tr["tambem_evento_inequivoco"] = [(u, t) in chave_nova for u, t in zip(tr.uasg, tr.t0)]
    j = P.pos
    st = P.arr["status"]
    def motivo(r):
        if r.tambem_evento_inequivoco:
            return "mesmo evento"
        i = j.get(r.uasg)
        a, b = st[i, P.j(r.t0) - 1], st[i, P.j(r.t0)]
        if MISTO in (a, b):
            return "trimestre misto em t0-1 ou t0"
        return "outro (regime inequívoco difere da regra de maioria)"
    tr["motivo"] = tr.apply(motivo, axis=1)
    return {"trocas_regra_anterior": int(len(tr)), "por_direcao": tr.direcao.value_counts().to_dict(),
            "tipos_regra_anterior": info.tipo.value_counts().to_dict(),
            "tambem_eventos_inequivocos": int(tr.tambem_evento_inequivoco.sum()),
            "motivos": tr.motivo.value_counts().to_dict(),
            "painel_regra_anterior": f"{comum.nome_tri(ti)}–{comum.nome_tri(E['tri_fim'])}"}, tr


def executar(c, P, log):
    st = P.arr["status"]
    ev = eventos(st, P.t_ini, P.unidades, P.attr["cnpj"])
    d = c["desenho"]
    t_p0, t_p1 = comum.tri(c["periodo"]["preco_primeiro"]), comum.tri(c["periodo"]["preco_ultimo"])
    f0 = min(d["formacao"])
    ev["janela_principal_calendario"] = (ev.t0 + f0 >= t_p0) & (ev.t0 <= t_p1)
    fc = min(d["janela_curta"]["formacao"])
    ev["janela_curta_calendario"] = (ev.t0 + fc >= t_p0) & (ev.t0 <= t_p1)
    ev["historico_curto_compativel"] = [
        all(h in (o, "sem_compras") for h in hm.split("|")[-(-fc - 1):]) for hm, o in zip(ev.historico_modos, ev.origem)]
    ev["id_evento"] = [f"{u}_{comum.nome_tri(t)}" for u, t in zip(ev.uasg, ev.t0)]
    frac = np.where(P.arr["n_compras_modo"] > 0, P.arr["n_af_modo"] / np.maximum(P.arr["n_compras_modo"], 1), np.nan)
    n_misto, por_t = perdas_por_misto(st, frac, P.t_ini)
    obs = st != NAO_OBS
    resumo = {
        "uasg_trimestres_observados": int(obs.sum()), "uasg_trimestres_A": int((st == A).sum()),
        "uasg_trimestres_AF": int((st == AF).sum()), "uasg_trimestres_mistos": int((st == MISTO).sum()),
        "fracao_mistos": float((st == MISTO).sum() / obs.sum()),
        "compras_em_trimestres_mistos": int(P.arr["n_compras_modo"][st == MISTO].sum()),
        "compras_total": int(P.arr["n_compras_modo"].sum()),
        "eventos_inequivocos_todos": int(len(ev)), "por_direcao": ev.direcao.value_counts().to_dict(),
        "por_persistencia": ev["persistencia_t0+1"].value_counts().to_dict(),
        "uasgs_com_evento": int(ev.uasg.nunique()), "cnpjs_com_evento": int(ev.cnpj.nunique()),
        "uasgs_com_mais_de_um_evento": int((ev.groupby("uasg").size() > 1).sum()),
        "trocas_por_maioria_perdidas_por_trimestre_misto": n_misto,
        "perdas_misto_por_trimestre": {comum.nome_tri(k): v for k, v in sorted(por_t.items())},
        "criterio": c["regime"]["_principal_nota"],
    }
    comp, tr = regra_anterior(c, P, ev)
    resumo["comparacao_regra_anterior"] = comp
    return ev, resumo, tr
