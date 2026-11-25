"""Orquestração com retomada segura: cada etapa grava um estado (hash do código e das saídas) e é pulada quando
o código e os arquivos produzidos conferem. Fase I (desenho) termina no congelamento; a Fase II só começa se o
protocolo congelado conferir."""
import numpy as np
import pandas as pd

from . import comum
from .comum import PASTA

TAB, RES, GRA = PASTA / "tabelas", PASTA / "resultados", PASTA / "graficos"


class Etapas:
    def __init__(self, c, log, refazer=()):
        self.c, self.log, self.refazer = c, log, set(refazer)
        self.cod = comum.hashes_codigo()

    def _estado(self, nome):
        return comum.trabalho(self.c, "estado", f"{nome}.json")

    def valida(self, nome, deps):
        p = self._estado(nome)
        if nome in self.refazer or not p.exists():
            return False
        e = comum.ler_json(p)
        if any(e["codigo"].get(k) != self.cod.get(k) for k in deps):
            return False
        for arq, h in e["saidas"].items():
            if not comum.resolver(arq).exists() or comum.sha(comum.resolver(arq)) != h:
                return False
        return True

    def gravar(self, nome, saidas):
        comum.escrever_json(self._estado(nome), {"etapa": nome, "concluida_em": comum.agora(), "codigo": self.cod,
                                                  "saidas": {str(s): comum.sha(s) for s in saidas}})

    def rodar(self, nome, deps, func):
        if self.valida(nome, deps + ["config.json"]):
            self.log(f"etapa {nome}: já concluída (hashes conferem) — pulada")
            return
        self.log(f"etapa {nome}: início")
        saidas = func()
        self.gravar(nome, saidas)
        self.log(f"etapa {nome}: concluída ({len(saidas)} arquivos)")


# ------------------------------------------------------------------------------------------- etapas 1–3

def etapa_fontes(c, log):
    from . import verificar_fontes
    verificar_fontes.executar(c, log)
    return [RES / "fontes.json"]


def etapa_painel(c, log):
    from . import construir_painel as cp
    from . import executar_placebos as plc
    f = comum.ler_json(RES / "fontes.json")
    ativ = cp.extrair_atividade(c, f["pncp_v2"]["caminho"], log)
    saidas = [ativ]
    resumos = {}
    for nome, pasta in (("S1", c["fontes"]["dados_S1"]), ("S1S2", c["fontes"]["dados_S1S2"])):
        P, cob, resumo = cp.construir(c, pasta, ativ, log, nome)
        plc.adicionar_derivadas(P)
        destino = comum.trabalho(c, f"painel_{nome}.pkl.gz")
        comum.salvar_pkl(destino, P)
        saidas.append(destino)
        resumos[nome] = resumo
        if nome == "S1":
            comum.escrever_csv(TAB / "cobertura_indice_trimestres.csv", cob.to_dict("records"))
            saidas.append(TAB / "cobertura_indice_trimestres.csv")
        log(f"painel {nome}: {resumo}")
    comum.escrever_json(RES / "painel_resumo.json", resumos)
    return saidas + [RES / "painel_resumo.json"]


def etapa_eventos(c, log):
    from . import identificar_eventos as ie
    P = comum.ler_pkl(comum.trabalho(c, "painel_S1.pkl.gz"))
    ev, resumo, tr = ie.executar(c, P, log)
    comum.salvar_pkl(comum.trabalho(c, "eventos.pkl.gz"), ev)
    comum.escrever_csv(TAB / "eventos_identificados.csv", ev.drop(columns=["u"]).to_dict("records"))
    comum.escrever_csv(TAB / "regra_anterior_comparacao.csv",
                       tr[["uasg", "cnpj", "d0", "F", "direcao", "t0", "puro", "absorvente", "tambem_evento_inequivoco", "motivo"]]
                       .to_dict("records"))
    comum.escrever_json(RES / "eventos_resumo.json", resumo)
    log(f"eventos: {resumo['eventos_inequivocos_todos']} inequívocos; regra anterior {resumo['comparacao_regra_anterior']}")
    return [comum.trabalho(c, "eventos.pkl.gz"), TAB / "eventos_identificados.csv", TAB / "regra_anterior_comparacao.csv",
            RES / "eventos_resumo.json"]


# ------------------------------------------------------------------------------------------- Fase I

DESENHOS = [("principal", "S1", False, None), ("curta", "S1", True, [("M0", None)]), ("S1S2", "S1S2", False, [("M0", None)])]


def etapa_desenho(c, log):
    from . import desenho as ds
    from . import diagnosticar_balanceamento as bal
    from . import executar_placebos as plc
    ev = comum.ler_pkl(comum.trabalho(c, "eventos.pkl.gz"))
    inf = c["inferencia"]
    saidas, pares_all, plac_all, funis, desc, bal_all, balt, conc, psd, rsk, rtm_all = [], [], [], [], [], [], [], [], [], [], []
    for nome, amostra, curta, metodos in DESENHOS:
        P = comum.ler_pkl(comum.trabalho(c, f"painel_{amostra}.pkl.gz"))
        log(f"desenho {nome}: conjuntos de risco, PS e pareamento")
        s = ds.executar(c, P, ev, nome, curta, metodos, log)
        comum.salvar_pkl(comum.trabalho(c, f"desenho_{nome}.pkl.gz"), s)
        saidas.append(comum.trabalho(c, f"desenho_{nome}.pkl.gz"))
        pr = s["pares"]
        pares_all.append(pr)
        for m in sorted(pr.metodo.unique()):
            f = ds.funil(s, m)
            f.insert(0, "metodo", m)
            f.insert(0, "desenho", nome)
            funis.append(f)
            b = ds.balanceamento(s, m)
            b.insert(0, "desenho", nome)
            bal_all.append(b)
            pm = pr[(pr.metodo == m) & pr.balanceado]
            conc.append({"desenho": nome, "metodo": m, **bal.concentracao(pm)})
            # placebo reservado t−2 → t−1 (Fase I)
            L, out = plc.placebo(P, pm, -1, -2, B=inf["wcr_B"], semente=c["semente"], margem=inf["margem_equivalencia_lp"])
            for o in out:
                plac_all.append({"desenho": nome, "metodo": m, "placebo": "reservado_t-2_t-1", **o})
            # data fictícia t−4 → t−3 (em M1 é mecânico)
            L2, out2 = plc.placebo(P, pm, -3, -4, B=inf["wcr_B"], semente=c["semente"], margem=inf["margem_equivalencia_lp"])
            for o in out2:
                plac_all.append({"desenho": nome, "metodo": m, "placebo": "data_ficticia_t-4_t-3" + (" (mecânico: preços usados em M1)" if m == "M1" else ""), **o})
            if nome == "principal":
                for var in ("srp_tri", "sigilo_tri", "logq_tri", "log_compras_tri", "log_itens_tri"):
                    L3 = plc.montar_linhas(P.ate, pm, -1, -2, var, "nC")
                    if len(L3):
                        from . import inferencia
                        r = inferencia.contraste(L3, None, B=0, margem=None)
                        plac_all.append({"desenho": nome, "metodo": m, "placebo": f"caracteristica_{var}_t-2_t-1", "grupo": "agregado", **r})
                d_rtm, r_rtm = plc.regressao_media(P, pm, pd.concat(s["pop"].values(), ignore_index=True))
                rtm_all.append({"desenho": nome, "metodo": m, **r_rtm})
        if nome == "principal":
            balt.append(ds.balanceamento_por_t0(s, "M0"))
        md = ds.motivos_descarte(s, "M0")
        md.insert(0, "desenho", nome)
        desc.append(md)
        for direcao, d in s["ps"].items():
            psd.append({"desenho": nome, "direcao": direcao, **d["diag"]})
            cal = d["calibracao"].copy()
            cal.insert(0, "direcao", direcao)
            cal.insert(0, "desenho", nome)
            comum.escrever_csv(TAB / f"propensao_calibracao_{nome}_{direcao.replace('->', '_')}.csv", cal.to_dict("records"))
            saidas.append(TAB / f"propensao_calibracao_{nome}_{direcao.replace('->', '_')}.csv")
            # distribuição dos scores (tratadas × candidatas) para o gráfico
            r = s["pop"][direcao]
            comum.escrever_csv(TAB / f"propensao_scores_{nome}_{direcao.replace('->', '_')}.csv",
                               r[["u", "t0", "y", "logit_ps", "ps"]].to_dict("records"))
            saidas.append(TAB / f"propensao_scores_{nome}_{direcao.replace('->', '_')}.csv")
        t = s["tab_risco"].copy()
        t.insert(0, "desenho", nome)
        rsk.append(t)
        del P
    pares = pd.concat(pares_all, ignore_index=True)
    import pandas as _pd
    tr_ant = _pd.read_csv(TAB / "regra_anterior_comparacao.csv", dtype={"uasg": str, "cnpj": str})
    viab, dens = ds.viabilidade(c, comum.ler_pkl(comum.trabalho(c, "painel_S1.pkl.gz")), ev, tr_ant)
    escrever = [("viabilidade_regras_alternativas.csv", viab), ("funil_suporte.csv", pd.concat(funis)), ("balanceamento.csv", pd.concat(bal_all)),
                ("balanceamento_por_trimestre_M0.csv", pd.concat(balt)), ("placebos_reservados.csv", pd.DataFrame(plac_all)),
                ("eventos_descartados_e_mantidos.csv", pd.concat(desc).drop(columns=["u"])),
                ("conjuntos_risco.csv", pd.concat(rsk)), ("concentracao_controles.csv", pd.DataFrame(conc)),
                ("propensao_diagnosticos.csv", pd.DataFrame(psd)), ("regressao_media.csv", pd.DataFrame(rtm_all))]
    for n, df in escrever:
        comum.escrever_csv(TAB / n, df.to_dict("records"))
        saidas.append(TAB / n)
    # congelamento
    cols = ["desenho", "metodo", "id_evento", "t0", "direcao", "sinal_af", "u_tratada", "uasg_tratada", "cnpj_tratada",
            "u_controle", "uasg_controle", "cnpj_controle", "ordem", "distancia_mahalanobis", "logit_ps_tratada",
            "logit_ps_controle", "dif_logit_ps", "peso", "balanco_evento", "balanceado", "covariaveis", "motivo_inclusao"]
    pares = pares[cols].sort_values(["desenho", "metodo", "id_evento", "ordem"]).reset_index(drop=True)
    comum.escrever_parquet(RES / "pares_congelados.parquet", pares)
    principal = pares[(pares.desenho == "principal") & (pares.metodo == "M0") & pares.balanceado]
    ev_sh = principal.drop_duplicates("id_evento").cnpj_tratada.value_counts(normalize=True)
    sm = c["matching"]["suporte_minimo"]
    n_ef = float(1 / np.sum(ev_sh ** 2)) if len(ev_sh) else 0.0
    bal_m0 = pd.concat(bal_all)
    bal_m0 = bal_m0[(bal_m0.desenho == "principal") & (bal_m0.metodo == "M0")]
    from . import construir_covariaveis as cv
    bm0 = bal_m0[bal_m0.covariavel.isin(cv.M0_CONT)]
    pl = pd.DataFrame(plac_all)
    plm = pl[(pl.desenho == "principal") & (pl.metodo == "M0") & (pl.placebo == "reservado_t-2_t-1") & (pl.grupo == "agregado")]
    diag = {"densidade_indice": dens, "eventos_principal_M0": int(principal.id_evento.nunique()), "n_efetivo_cnpjs_tratados": n_ef,
            "suporte_suficiente": bool(principal.id_evento.nunique() >= sm["eventos"] and n_ef >= sm["n_efetivo_cnpjs_tratados"]),
            "covariaveis_M0_com_smd_depois_maior_0_10": bm0.loc[bm0.smd_depois.abs() >= 0.10, "covariavel"].tolist(),
            "smd_abs_max_depois_M0": float(bm0.smd_depois.abs().max()) if len(bm0) else None,
            "placebo_reservado_M0": plm.iloc[0][["beta_lp", "ic95_inf", "ic95_sup", "p_t", "p_wcr_webb", "p_tost", "mde_80"]].to_dict() if len(plm) else None}
    comum.escrever_json(RES / "diagnostico_desenho.json", diag)
    prot = {"congelado_em": comum.agora(), "fase": "I (desenho) concluída; nenhum desfecho com t >= t0 foi acessado",
            "config_sha256": comum.sha(PASTA / "config.json"), "codigo_sha256": comum.hashes_codigo(),
            "fontes_sha256": comum.sha(RES / "fontes.json"), "pares_sha256_conteudo": comum.hash_df(pares),
            "pares_linhas": int(len(pares)), "desenhos": [d[0] for d in DESENHOS],
            "metodos": sorted(pares.groupby(["desenho", "metodo"]).size().index.map("/".join)),
            "especificacao_principal": "desenho principal, M0, pares com balanceamento de evento satisfatório, h = 0, peso igual por evento, índice C1 (compra-média), referência A1 da S1",
            "robustez_predefinida": [f"R{i}" for i in range(1, 18)], "diagnostico_desenho": diag,
            "declaracao": ("suporte suficiente pelos critérios predefinidos" if diag["suporte_suficiente"] else
                           "SUPORTE INSUFICIENTE pelos critérios predefinidos: estimativas da Fase II são apenas descritivas")}
    comum.escrever_json(RES / "protocolo_congelado.json", prot)
    man = {"gerado_em": comum.agora(), "pares_congelados.parquet": comum.sha(RES / "pares_congelados.parquet"),
           "pares_sha256_conteudo": prot["pares_sha256_conteudo"], "protocolo_congelado.json": comum.sha(RES / "protocolo_congelado.json"),
           "tabelas_fase_I": {n: comum.sha(TAB / n) for n, _ in escrever}}
    comum.escrever_json(RES / "manifesto_matching.json", man)
    log(f"Fase I congelada: {prot['declaracao']}; {diag['eventos_principal_M0']} eventos no principal")
    return saidas + [RES / "pares_congelados.parquet", RES / "protocolo_congelado.json", RES / "manifesto_matching.json",
                     RES / "diagnostico_desenho.json"]
