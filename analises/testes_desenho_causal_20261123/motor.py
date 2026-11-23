"""Motor do estudo de eventos por unidade compradora (protocolo.md, §3–§5).

Para cada evento k (unidade u_k, mês m_k, sentido A->AF ou AF->A) e um desfecho por compra y:
    Δ_u   = média de y nas compras de [m_k, m_k+W-1] − média de y nas compras de [m_k−W, m_k−1]
    DiD_k = Δ_{u_k} − média de Δ_j nos controles limpos C_k
C_k: unidades da mesma esfera, com >= cmin compras com y em cada meia janela e estáveis no modo de partida nas duas
meias janelas (parcela de AF <= 10% para A->AF; >= 90% para AF->A); exclui unidades com evento na janela.
Perfil por trimestre de evento (b = −W/3, …, W/3 − 1), base b = −1: β_b,k = (ȳ_b − ȳ_{−1})_{u_k} − média nos controles.
"""
import numpy as np
import pandas as pd


class Paineis:
    def __init__(self, P, m_fim_desfecho):
        self.P = P
        self.U, self.M = P["N"].shape
        self.mf = int(m_fim_desfecho)                     # meses de desfecho válidos: 0..mf-1
        self._cs = {}

    def cs(self, k):
        if k not in self._cs:
            x = self.P[k]
            self._cs[k] = np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, 1)], 1)
        return self._cs[k]

    def soma(self, k, a, b):
        """soma de P[k] nos meses [a, b) para todas as unidades."""
        c = self.cs(k)
        a, b = max(a, 0), min(b, c.shape[1] - 1)
        return c[:, b] - c[:, a]


def janela_ok(m, W, mf):
    return (m - W >= 0) and (m + W <= mf)


def did_eventos(pn, ev, y="e", W=6, cmin=3, base_por_tipo=True, controle="esfera", unid=None,
                ev_todos=None, nunca=None, guardar_controles=False, reg=("N", "A"), lim=(0.10, 0.90),
                perfil=True, Sk=None, Ck=None, cego=False):
    """Calcula DiD_k para cada evento de `ev` (DataFrame com u, m, tipo, esfera). Devolve DataFrame por evento.
    unid: DataFrame das unidades (índice u) com esfera; ev_todos: todos os eventos (para excluir unidades com evento
    na janela); nunca: se dado, conjunto de unidades permitidas como controle (ex.: só as estáveis no período todo).
    cego=True: não calcula nada da unidade tratada além das contagens (para o cálculo de poder do pré-registro)."""
    Sk = Sk or f"S_{y}"
    Ck = Ck or f"C_{y}"
    esf = unid.esfera.reindex(range(pn.U)).to_numpy()
    tem_ev = {}
    if ev_todos is not None:
        for u, m in zip(ev_todos.u, ev_todos.m):
            tem_ev.setdefault(int(u), []).append(int(m))
    nb = 2 * W // 3
    linhas, ctrl = [], {}
    for k, r in ev.iterrows():
        u, m = int(r.u), int(r.m)
        if not janela_ok(m, W, pn.mf):
            continue
        Spre, Cpre = pn.soma(Sk, m - W, m), pn.soma(Ck, m - W, m)
        Spos, Cpos = pn.soma(Sk, m, m + W), pn.soma(Ck, m, m + W)
        if Cpre[u] < cmin or Cpos[u] < cmin:
            continue
        Npre, Apre = pn.soma(reg[0], m - W, m), pn.soma(reg[1], m - W, m)
        Npos, Apos = pn.soma(reg[0], m, m + W), pn.soma(reg[1], m, m + W)
        with np.errstate(invalid="ignore", divide="ignore"):
            spre, spos = Apre / Npre, Apos / Npos
            ypre, ypos = Spre / Cpre, Spos / Cpos
        d = ypos - ypre
        if r.tipo == "A->AF":
            estavel = (spre <= lim[0]) & (spos <= lim[0])
        else:
            estavel = (spre >= lim[1]) & (spos >= lim[1])
        ok = (Cpre >= cmin) & (Cpos >= cmin) & estavel
        if controle == "esfera":
            ok &= esf == esf[u]
        if nunca is not None:
            ok &= np.isin(np.arange(pn.U), nunca)
        ok[u] = False
        for v, ms in tem_ev.items():
            if any(abs(mm - m) < W for mm in ms):
                ok[v] = False
        idx = np.where(ok)[0]
        if len(idx) < 5:
            continue
        du = np.nan if cego else float(d[u])
        lin = {"k": k, "u": u, "m": m, "tipo": r.tipo, "sinal": 1 if r.tipo == "A->AF" else -1,
               "delta_tratada": du, "delta_controles": float(d[idx].mean()), "did": du - float(d[idx].mean()),
               "n_controles": int(len(idx)), "c_pre": int(Cpre[u]), "c_pos": int(Cpos[u]),
               "af_pre": float(spre[u]), "af_pos": float(spos[u]),
               "primeiro_estagio": float((spos[u] - spre[u]) - np.nanmean(spos[idx] - spre[idx]))}
        if perfil and not cego:
            ys, cs_ = [], []
            for b in range(-nb // 2, nb // 2):
                a0 = m + 3 * b
                Sb, Cb = pn.soma(Sk, a0, a0 + 3), pn.soma(Ck, a0, a0 + 3)
                with np.errstate(invalid="ignore", divide="ignore"):
                    ys.append(Sb / Cb)
                cs_.append(Cb)
            ys, cs_ = np.array(ys), np.array(cs_)
            iref = nb // 2 - 1                              # posição do bin −1
            for jb, b in enumerate(range(-nb // 2, nb // 2)):
                if b == -1:
                    continue
                okb = ok & (cs_[jb] >= 1) & (cs_[iref] >= 1)
                if cs_[jb][u] >= 1 and cs_[iref][u] >= 1 and okb.sum() >= 5:
                    db = ys[jb] - ys[iref]
                    lin[f"b{b}"] = float(db[u] - db[okb].mean())
                else:
                    lin[f"b{b}"] = np.nan
        linhas.append(lin)
        if guardar_controles:
            ctrl[k] = pd.DataFrame({"u": idx, "dev": d[idx] - d[idx].mean(), "h": 1 / Cpre[idx] + 1 / Cpos[idx]})
        lin["h"] = float(1 / Cpre[u] + 1 / Cpos[u])
    out = pd.DataFrame(linhas)
    if guardar_controles:
        return out, ctrl
    return out


def matriz_eventos(df, col="did", pooled=True):
    """Desenho para média por sentido (X = [1{A->AF}, 1{AF->A}]) ou agregado com sinal (X = 1, y = sinal·did)."""
    if pooled:
        return np.ones((len(df), 1)), (df.sinal * df[col]).to_numpy(float)
    X = np.column_stack([(df.tipo == "A->AF").astype(float), (df.tipo == "AF->A").astype(float)])
    return X, df[col].to_numpy(float)


# ------------------------------------------------------------------------------------------- DiD sintético
def _fw_simplex(Aq, bq, eta, iters=3000, tol=1e-10):
    """min ||A x - b||² + eta ||x||² em x no simplex (Frank–Wolfe com busca exata)."""
    n = Aq.shape[1]
    x = np.full(n, 1.0 / n)
    r = Aq @ x - bq
    for _ in range(iters):
        g = 2 * Aq.T @ r + 2 * eta * x
        i = int(np.argmin(g))
        dvec = -x.copy(); dvec[i] += 1.0
        Ad = Aq[:, i] - Aq @ x
        num = -(g @ dvec)
        den = 2 * (Ad @ Ad + eta * (dvec @ dvec))
        if den <= 0 or num <= tol:
            break
        gam = min(1.0, num / den)
        x = x + gam * dvec
        r = Aq @ x - bq
    return x


def sdid(Y, T0):
    """Y: (N0+1) x T, última linha tratada. Arkhangelsky et al. (2021), um tratado. Devolve τ e pesos."""
    Y0, y1 = Y[:-1], Y[-1]
    N0, T = Y0.shape
    T1 = T - T0
    dif = np.diff(Y0[:, :T0], axis=1)
    sig = float(np.std(dif)) if dif.size > 1 else 0.0
    zeta = (1 * T1) ** 0.25 * sig
    # pesos de unidade: com intercepto -> centrar no tempo (pré)
    Ap = Y0[:, :T0].T                                     # T0 x N0
    Ap_c = Ap - Ap.mean(0, keepdims=True)
    bp_c = y1[:T0] - y1[:T0].mean()
    om = _fw_simplex(Ap_c, bp_c, zeta ** 2 * T0)
    # pesos de tempo: com intercepto -> centrar entre unidades
    At = Y0[:, :T0]                                       # N0 x T0
    bt = Y0[:, T0:].mean(1)
    At_c = At - At.mean(0, keepdims=True)
    bt_c = bt - bt.mean()
    la = _fw_simplex(At_c, bt_c, (1e-6 * sig) ** 2 * N0)
    tau = (y1[T0:].mean() - la @ y1[:T0]) - om @ (Y0[:, T0:].mean(1) - Y0[:, :T0] @ la)
    return float(tau), om, la
