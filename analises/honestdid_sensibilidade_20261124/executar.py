"""Sensibilidade HonestDiD (Rambachan e Roth, 2023) do estudo de eventos A × AF (protocolo.md). EXPLORATÓRIO.

Comando único (da pasta PNCP-Automation):
    python analises/honestdid_sensibilidade_20261124/executar.py
Etapas:
  1. coeficientes.py: reprodução do M0 e do perfil de 23/11; vetores dinâmicos, matrizes de covariância conjuntas por
     órgão e entradas do R (entradas/);
  2. executar.R pelo Rscript: pacote oficial HonestDiD (Δ^RM com C-LF; Δ^SD com FLCI; Δ^SDRM com ≥ 2 pré-períodos);
  3. conferências (conjunto identificado: pacote × programação linear) e tabelas-resumo;
  4. gráficos (graficos_honestdid.py);
  5. registro_execucao.json.
Rscript: variável HONESTDID_RSCRIPT; senão C:/Program Files/R/R-*/bin/Rscript.exe (o mais recente); senão o PATH.
Pré-requisitos: base de 23/11 em dados/testes_desenho_causal/; R com o pacote HonestDiD (install.packages("HonestDiD")).
Não lê o pncp.db; não altera bases nem resultados anteriores; não usa os eventos reservados (posteriores a 2025-10).
"""
import glob, hashlib, json, os, shutil, subprocess, sys, time, traceback
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(AQUI))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

TAB = AQUI / "tabelas"
LOG_R = RAIZ / "dados" / "honestdid_sensibilidade" / "executar_R.log"          # fora do git
REF, REF_IC, REF_F = -1.91, (-5.67, 1.93), -3.76
T0 = time.time()
REG = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S"), "classificacao": "exploratório",
       "protocolo_sha256": hashlib.sha256((AQUI / "protocolo.md").read_bytes()).hexdigest(),
       "parametros": {"alfa": 0.05, "Mbar": [0, 0.5, 1, 1.5, 2, 3], "M_lp_por_trimestre": [0, 0.25, 0.5, 1, 1.5, 2, 3],
                      "metodo_RM": "C-LF (padrão do pacote)", "metodo_SD": "FLCI (padrão do pacote para Δ^SD)",
                      "bootstrap_covariancia_B": 9999, "semente": 20261124, "influencia_valores": {"Mbar": 1, "M": 1},
                      "tolerancia_quebra": 0.01, "minimo_eventos_coef": 30, "minimo_orgaos_coef": 20},
       "etapas": {}, "conferencias": {}, "falhas": [], "limitacoes": []}


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def etapa(nome, f):
    t = time.time()
    try:
        r = f()
        REG["etapas"][nome] = {"status": "ok", "segundos": round(time.time() - t, 1)}
        return r
    except Exception as e:  # noqa: BLE001
        REG["etapas"][nome] = {"status": "falhou", "erro": repr(e), "segundos": round(time.time() - t, 1),
                               "traceback": traceback.format_exc()[-2000:]}
        REG["falhas"].append(f"{nome}: {e!r}")
        log("FALHOU", nome, repr(e))
        return None


def rscript():
    p = os.environ.get("HONESTDID_RSCRIPT")
    if p and Path(p).exists():
        return p
    c = sorted(glob.glob("C:/Program Files/R/R-*/bin/Rscript.exe"))
    return c[-1] if c else shutil.which("Rscript")


# --------------------------------------------------------------------------------------------- etapas
def e1():
    import coeficientes as CO
    r = CO.main(log=log)
    for k in ("conferencias", "exclusoes"):
        REG[k] = {**REG.get(k, {}), **r[k]}
    for k in ("especificacoes", "reproducao", "M0", "M1", "janela_12"):
        REG[k] = r[k]
    if not r["conferencias"].get("reproducao_ok"):
        raise RuntimeError("a reprodução do M0 ou do perfil de 23/11 falhou")
    return r


def e2():
    rs = rscript()
    if rs is None:
        raise RuntimeError("Rscript não encontrado (defina HONESTDID_RSCRIPT)")
    LOG_R.parent.mkdir(parents=True, exist_ok=True)
    for f in TAB.glob("*_refeitos.csv"):                  # sobras de reexecuções parciais não valem numa rodada completa
        f.unlink()
    REG["rscript"] = rs
    p = subprocess.run([rs, str(AQUI / "executar.R"), str(AQUI)], cwd=str(RAIZ), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    LOG_R.write_text(p.stdout + "\n--- stderr ---\n" + p.stderr, encoding="utf-8", newline="\n")
    REG["saida_R"] = p.stdout.strip().splitlines()[-3:]
    if p.returncode != 0:
        raise RuntimeError(f"executar.R terminou com código {p.returncode}; ver {LOG_R}")
    amb = pd.read_csv(TAB / "r_ambiente.csv")
    REG["ambiente_R"] = dict(zip(amb.chave, amb.valor))
    return True


def e3():
    for base in ("honestdid_resultados", "honestdid_quebras"):
        f_ref = TAB / f"{base}_refeitos.csv"
        if f_ref.exists():                                 # reexecução parcial de linhas (HONESTDID_SO_IDS)
            tot, ref = pd.read_csv(TAB / f"{base}.csv"), pd.read_csv(f_ref)
            tot = pd.concat([tot[~tot.id.isin(ref.id)], ref], ignore_index=True)
            tot = tot.sort_values([c for c in ("espec", "parametro", "familia", "valor") if c in tot.columns])
            tot.to_csv(TAB / f"{base}.csv", index=False, lineterminator=chr(10))
            if base == "honestdid_resultados":
                REG["linhas_refeitas"] = {"ids": sorted(ref.id.unique().tolist()), "motivo":
                                          "falha numérica do FLCI do pacote num valor de M derrubava a chamada inteira; "
                                          "refeitas com avaliação valor a valor (o executar.R atual já faz isso direto)"}
    res = pd.read_csv(TAB / "honestdid_resultados.csv")
    py = pd.read_csv(TAB / "conjunto_identificado_python.csv")
    m = res.merge(py, on=["id", "familia", "valor"], how="inner")
    viavel = m.id_lb_py.notna()
    dl, du = (m.id_lb - m.id_lb_py).abs()[viavel], (m.id_ub - m.id_ub_py).abs()[viavel]
    inv = m[~viavel]
    reserva = np.isclose(inv.id_lb, inv.estimativa_lp) & np.isclose(inv.id_ub, inv.estimativa_lp)
    REG["conferencias"]["conjunto_identificado_pacote_vs_programacao_linear"] = {
        "comparacoes": int(len(m)), "viaveis": int(viavel.sum()), "max_dif_lp_viaveis": float(np.nanmax(np.r_[dl, du])),
        "inviaveis_na_programacao_linear": int((~viavel).sum()),
        "inviaveis_em_que_o_pacote_devolve_l_beta_pos": int(reserva.sum()),
        "nota": "quando os pré-coeficientes violam Δ^SD(M), o conjunto identificado em β = β̂ é vazio; a função interna do "
                "pacote avisa 'Solver did not find an optimum' e devolve l′β̂_pós (reserva); o relatório usa 'vazio'",
        "ok": bool(np.nanmax(np.r_[dl, du]) < 1e-6 and reserva.all())}
    vazio = res.merge(py, on=["id", "familia", "valor"], how="left").id_lb_py.isna().to_numpy() & res.familia.eq("SD").to_numpy()
    res.loc[vazio, ["id_lb", "id_ub"]] = np.nan
    res["conjunto_identificado_vazio"] = vazio
    REG["conferencias"]["erros_no_R"] = int(res.groupby("id").erro.apply(lambda s: s.fillna("").str.len().gt(0).any()).sum())
    REG["conferencias"]["IC_tocando_a_grade_do_C-LF"] = int(res.toca_grade_rm.sum())
    # resumo por especificação, parâmetro, família e valor
    comp = res[res.grade == "completa"]
    orig = comp[comp.familia == "original"][["id", "lb", "ub"]].rename(columns={"lb": "lb_original", "ub": "ub_original"})
    s = comp[comp.familia != "original"].merge(orig, on="id")
    s["largura"] = s.ub - s.lb
    s["razao_largura_vs_original"] = s.largura / (s.ub_original - s.lb_original)
    s["maior_reducao_compativel_lp"] = np.where(s.lb < 0, -s.lb, 0.0)
    s["maior_aumento_compativel_lp"] = np.where(s.ub > 0, s.ub, 0.0)
    s["inclui_-1,91"] = (s.lb <= REF) & (s.ub >= REF)
    s["dif_estimativa_vs_-1,91"] = s.estimativa_lp - REF
    s["centro_conjunto_identificado"] = (s.id_lb + s.id_ub) / 2
    esp = pd.read_csv(TAB / "especificacoes.csv")
    s = s.merge(esp[["espec", "descricao", "amostra", "eventos", "orgaos", "orgaos_efetivos", "numPre", "numPost"]],
                on="espec", how="left")
    cols = ["id", "espec", "descricao", "amostra", "parametro", "familia", "valor", "estimativa_lp", "dif_estimativa_vs_-1,91",
            "lb_original", "ub_original", "lb", "ub", "largura", "razao_largura_vs_original", "inclui_zero", "inclui_-1,91",
            "maior_reducao_compativel_lp", "maior_aumento_compativel_lp", "id_lb", "id_ub", "conjunto_identificado_vazio",
            "centro_conjunto_identificado",
            "eventos", "orgaos", "orgaos_efetivos", "numPre", "numPost", "metodo", "delta", "toca_grade_rm", "erro"]
    s[cols].to_csv(TAB / "honestdid_resumo.csv", index=False, lineterminator="\n")
    # influência
    loo = res[res.grade == "loo"]
    if len(loo):
        infl = pd.read_csv(TAB / "influencia_orgaos_coeficientes.csv")
        lr = loo[loo.familia.isin(["RM", "SD", "original"])]
        w = lr.pivot_table(index="espec", columns=["parametro", "familia"], values=["lb", "ub"])
        w.columns = [f"{p}_{f}_{v}" for v, p, f in w.columns]
        w = infl.merge(w.reset_index(), left_on="id", right_on="espec", how="left").drop(columns="espec")
        w.to_csv(TAB / "honestdid_influencia_orgaos.csv", index=False, lineterminator="\n")
        resumo = {}
        for p in ("a", "b"):
            for f in ("RM", "SD"):
                lb, ub = w[f"{p}_{f}_lb"], w[f"{p}_{f}_ub"]
                cheia = comp[(comp.espec == "P1") & (comp.parametro == p) & (comp.familia == f) & (comp.valor == 1.0)]
                resumo[f"{p}_{f}"] = {"amostra_completa": [float(cheia.lb.iloc[0]), float(cheia.ub.iloc[0])] if len(cheia) else None,
                                      "lb_min_max": [float(lb.min()), float(lb.max())],
                                      "ub_min_max": [float(ub.min()), float(ub.max())],
                                      "retiradas_em_que_o_IC_exclui_zero": int(((lb > 0) | (ub < 0)).sum()),
                                      "retiradas": int(len(w))}
        REG["influencia_orgaos"] = resumo
    if (TAB / "honestdid_quebras.csv").exists():
        q = pd.read_csv(TAB / "honestdid_quebras.csv")
        REG["quebras"] = {"aplicaveis": q[q.aplica == True][["id", "familia", "quebra", "nota"]].to_dict("records"),  # noqa: E712
                          "combinacoes": int(len(q)), "nao_aplicaveis_IC_ja_inclui_zero": int((q.aplica != True).sum())}  # noqa: E712
    return True


def e4():
    import graficos_honestdid as G
    return G.main(AQUI)


def main():
    e1r = etapa("1_coeficientes_e_matrizes", e1)
    if e1r is not None:
        ok2 = etapa("2_honestdid_R", e2)
        if ok2:
            etapa("3_conferencias_e_resumos", e3)
    g = etapa("4_graficos", e4)
    if g:
        REG["graficos"] = g.get("graficos")
    REG["limitacoes"] = [
        "Janela principal com 1 pré-período (trimestre −2): Δ^RM usa um único coeficiente impreciso como magnitude pré; "
        "Δ^SD não tem informação pré sobre curvatura; Δ^SDRM não se aplica.",
        "Os coeficientes dinâmicos têm eventos diferentes por trimestre (110, 136, 120) e não reproduzem o estimando do M0 "
        "(ver tabelas/diferenca_estimando.csv).",
        "Janela de 12 meses: trimestres −4 e −3 com 13–27 eventos e 10–19 órgãos (baixa precisão); amostra de 78 eventos.",
        "O pacote trata β̂ como normal com V conhecida; V é estimada por agrupamento em 57–68 órgãos por coeficiente.",
        "Exploratório: nenhum teste confirmatório; os 56 eventos reservados não foram usados."]
    REG["fim"] = time.strftime("%Y-%m-%d %H:%M:%S")
    REG["segundos_total"] = round(time.time() - T0, 1)
    (AQUI / "registro_execucao.json").write_text(json.dumps(REG, ensure_ascii=False, indent=1, default=str),
                                                 encoding="utf-8", newline="\n")
    log("fim", {k: v["status"] for k, v in REG["etapas"].items()})


if __name__ == "__main__":
    main()
