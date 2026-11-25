"""Mundo sintético para os testes: painel UASG × trimestre com regime, índice e atividade conhecidos."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))

from scripts import comum  # noqa: E402
from scripts import identificar_eventos as ie  # noqa: E402
from scripts.construir_painel import A, AF, MISTO, NAO_OBS, Painel  # noqa: E402

T_INI, T_FIM = comum.tri("2023T1"), comum.tri("2026T4")
P0, P1 = comum.tri("2023T2"), comum.tri("2026T1")


def cfg():
    return comum.cfg()


def painel(status, Y, cnpj=None, esfera=None, itens=None, seed=0):
    """status, Y: U × T (T = 16, 2023T1..2026T4). Y fora de 2023T2..2026T1 é ignorado (NaN)."""
    rng = np.random.default_rng(seed)
    U, T = status.shape
    unidades = [f"{900000 + i:06d}" for i in range(U)]
    P = Painel(unidades, T_INI, T_FIM)
    P.arr["status"] = status.astype(np.int8)
    obs = (status != NAO_OBS).astype(float)
    Yv = Y.copy().astype(float)
    Yv[:, : P0 - T_INI] = np.nan
    Yv[:, P1 - T_INI + 1:] = np.nan
    Yv[status == NAO_OBS] = np.nan
    P.arr["Yc"] = Yv
    P.arr["Yi"] = Yv.copy()
    P.arr["nC"] = np.isfinite(Yv) * 2.0
    P.arr["nI"] = np.isfinite(Yv) * 5.0
    het = rng.normal(0, 1, (U, 6))                      # heterogeneidade institucional (só covariáveis pré)
    base = (itens if itens is not None else np.round(30 * np.exp(0.3 * het[:, 0])))[:, None] * np.ones((1, T))
    P.arr["n_compras"] = obs * 3
    P.arr["n_compras_modo"] = obs * 3
    P.arr["n_af_modo"] = np.where(status == AF, 3, np.where(status == MISTO, 1, 0)) * obs
    P.arr["it_n"] = obs * base
    P.arr["lv_soma"] = obs * 3 * (10 + 0.3 * het[:, 1])[:, None]
    P.arr["lv_n"] = obs * 3
    P.arr["n_itens_s1"] = obs * 10
    P.arr["logq_soma"] = obs * 10 * (2 + 0.3 * het[:, 2])[:, None]
    P.arr["logq_n"] = obs * 10
    P.arr["n_srp"] = obs * np.clip(np.round(1.5 + het[:, 3]), 0, 3)[:, None]
    P.arr["it_sig"] = obs * 3
    P.arr["it_decid"] = obs * 25
    P.arr["it_hom"] = obs * np.clip(np.round(20 + 2 * het[:, 4]), 0, 25)[:, None]
    P.arr["it_frac"] = obs * 3
    P.arr["it_des"] = obs * 2
    from scripts.executar_placebos import adicionar_derivadas
    adicionar_derivadas(P)
    P.attr["cnpj"] = np.array(cnpj if cnpj is not None else [f"C{i // 2:03d}" for i in range(U)])
    P.attr["esfera"] = np.array(esfera if esfera is not None else ["F"] * U)
    P.attr["poder"] = np.array(["E"] * U)
    P.attr["uf"] = np.array(["PB" if i % 2 else "SP" for i in range(U)])
    P.attr["_classes_top"] = np.array([100, 101, 102])
    pl, cl, it = [], [], []
    for u in range(U):
        for j in range(T):
            if status[u, j] == NAO_OBS:
                continue
            t = T_INI + j
            pl.append({"u": u, "t": t, "produto": f"P{u % 5}", "n": 10})
            cl.append({"u": u, "t": t, "classe": 100 + u % 3, "n": int(base[u, j])})
            if np.isfinite(Yv[u, j]):
                it.append({"u": u, "t": t, "chave": f"{u}-{t}", "produto": f"P{(u + t) % 4}", "classe": 100 + u % 3, "y_A1": Yv[u, j]})
    P.longo["produtos_licitados"] = pd.DataFrame(pl)
    P.longo["classes"] = pd.DataFrame(cl)
    P.longo["itens_y"] = pd.DataFrame(it, columns=["u", "t", "chave", "produto", "classe", "y_A1"])
    return P


def anotar(c, P):
    ev = ie.eventos(P.arr["status"], P.t_ini, P.unidades, P.attr["cnpj"])
    d = c["desenho"]
    t_p0, t_p1 = comum.tri(c["periodo"]["preco_primeiro"]), comum.tri(c["periodo"]["preco_ultimo"])
    f0, fc = min(d["formacao"]), min(d["janela_curta"]["formacao"])
    ev["janela_principal_calendario"] = (ev.t0 + f0 >= t_p0) & (ev.t0 <= t_p1)
    ev["janela_curta_calendario"] = (ev.t0 + fc >= t_p0) & (ev.t0 <= t_p1)
    ev["historico_curto_compativel"] = [all(h in (o, "sem_compras") for h in hm.split("|")[-(-fc - 1):])
                                        for hm, o in zip(ev.historico_modos, ev.origem)]
    ev["id_evento"] = [f"{u}_{comum.nome_tri(t)}" for u, t in zip(ev.uasg, ev.t0)]
    return ev


def mundo_base(beta_af=-8.0, ruido=0.5, seed=1):
    """120 UASGs, 2 por CNPJ. 0–19 e 40–79 em A, 20–37 e 80–119 em AF, 38–39 em A com esfera M. Eventos em 2025T1 (t0):
    u0 e u2 adotam AF; u20 abandona; u38 adota (sem controle: o único da esfera M é do mesmo CNPJ); u10 adota mas
    sem índice em t−2; u6 (controle em t0) adota em t0+1; u4 adota em t0+1 e volta em t0+3 (evento repetido);
    u8 tem trimestre misto em 2024T3 e passa a AF em 2024T4 (sem evento inequívoco)."""
    rng = np.random.default_rng(seed)
    U, T = 120, T_FIM - T_INI + 1
    t0 = comum.tri("2025T1")
    j0 = t0 - T_INI
    st = np.full((U, T), A, dtype=int)
    st[20:38] = AF
    st[80:120] = AF                                     # 40–79: mais UASGs em A; 80–119: mais em AF
    for u in (0, 2, 10, 38):
        st[u, j0:] = AF
    st[20, j0:] = A
    st[6, j0 + 1:] = AF
    st[4, j0 + 1:j0 + 3] = AF
    st[8, comum.tri("2024T3") - T_INI] = MISTO
    st[8, comum.tri("2024T4") - T_INI:] = AF
    alfa = rng.normal(0, 5, U)
    delta = rng.normal(0, 3, T)
    Y = alfa[:, None] + delta[None, :] + beta_af * (st == AF) + rng.normal(0, ruido, (U, T))
    Y[10, j0 - 2] = np.nan
    esf = ["F"] * 38 + ["M", "M"] + ["F"] * 80
    return painel(st, Y, esfera=esf, seed=seed), t0
