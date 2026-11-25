"""Etapa 13 (Fase II): DiD pareado por evento e horizonte, depois do congelamento dos pares.

τ_{e,h} = (Y_{u,t0+h} − Y_{u,t0−1}) − Σ_v w_ev (Y_{v,t0+h} − Y_{v,t0−1}).
- Controles sem índice no horizonte saem do evento naquele horizonte (pesos renormalizados); evento sem tratada ou
  sem nenhum controle observado não é estimável naquele horizonte (perda registrada, nada é imputado).
- Censura: em h >= 1, o controle que deixou o regime de origem (ou ficou misto/sem compras) em algum trimestre
  t0+1..t0+h deixa de representar o contrafactual e sai SÓ daquele horizonte (continua no conjunto de risco de t0).
- Tratadas que revertem em t0+1 permanecem (estimando: efeito de ter trocado em t0, qualquer que seja a trajetória
  posterior); a sensibilidade 'persistentes' é selecionada pela trajetória e rotulada como tal.
- O acesso aos desfechos pós-tratamento só é liberado por `abrir_pos`, que confere o protocolo congelado.
"""
import numpy as np
import pandas as pd

from . import comum
from .construir_painel import A, AF


class PainelPos:
    def __init__(self, P):
        self._p = P

    def col(self, nome, t):
        j = int(t) - self._p.t_ini
        if j < 0 or j >= self._p.T:
            return np.full(len(self._p.unidades), np.nan)
        return self._p.arr[nome][:, j]


def abrir_pos(P, protocolo_path, pares_path):
    """Libera o painel completo SÓ se os pares congelados conferem com o protocolo (hash do conteúdo e do arquivo)."""
    prot = comum.ler_json(protocolo_path)
    pares = pd.read_parquet(pares_path)
    if comum.hash_df(pares) != prot["pares_sha256_conteudo"]:
        raise comum.ErroDesenho("pares_congelados.parquet não confere com protocolo_congelado.json")
    if comum.sha(comum.PASTA / "config.json") != prot["config_sha256"]:
        raise comum.ErroDesenho("config.json mudou depois do congelamento")
    return PainelPos(P), pares, prot


def _origem(direcao):
    return A if direcao == "A->AF" else AF


def montar_linhas(acesso, pares, rel_alvo, rel_base, ycol="Yc", ncol="nC", censura_ate=0, pesos="evento",
                  status=None, pesos_controle=None, eventos=None):
    """Linhas (evento, unidade) para o contraste. `acesso(t0)` devolve um objeto com .col(nome, t).
    rel_alvo pode ser lista (média dos horizontes, exigindo todos). pesos_controle: dict (id_evento, u) -> peso."""
    alvos = rel_alvo if isinstance(rel_alvo, (list, tuple)) else [rel_alvo]
    linhas = []
    for t0, g in pares.groupby("t0"):
        V = acesso(int(t0))
        Yb = V.col(ycol, t0 + rel_base)
        Ya = np.column_stack([V.col(ycol, t0 + r) for r in alvos])
        Na = V.col(ncol, t0 + alvos[0])
        st = None
        if censura_ate:
            st = np.column_stack([status.col("status", t0 + k) for k in range(1, censura_ate + 1)])
        for ide, ge in g.groupby("id_evento"):
            r0 = ge.iloc[0]
            u = int(r0.u_tratada)
            dz = np.nanmean(Ya[u]) - Yb[u] if np.isfinite(Ya[u]).all() else np.nan
            if not np.isfinite(dz):
                continue
            s = int(r0.sinal_af)
            o = _origem(r0.direcao)
            ctr = []
            for r in ge.itertuples():
                v = int(r.u_controle)
                if not (np.isfinite(Ya[v]).all() and np.isfinite(Yb[v])):
                    continue
                if st is not None and not (st[v] == o).all():
                    continue
                w = pesos_controle.get((ide, v), np.nan) if pesos_controle else 1.0
                if not np.isfinite(w):
                    continue
                ctr.append((v, r.uasg_controle, r.cnpj_controle, s * (np.nanmean(Ya[v]) - Yb[v]), w))
            if not ctr:
                continue
            cel = f"{r0.direcao}|{int(t0)}|{'+'.join(map(str, alvos))}"
            grupo = "adocao" if r0.direcao == "A->AF" else "abandono"
            linhas.append({"id_evento": ide, "papel": "T", "u": u, "uasg": r0.uasg_tratada, "cnpj": r0.cnpj_tratada,
                           "z": s * dz, "w": 1.0, "a": float(Na[u]) if pesos in ("compra", "item") else 1.0,
                           "grupo": grupo, "celula": cel, "t0": int(t0), "direcao": r0.direcao})
            for v, uv, cv_, z, w in ctr:
                linhas.append({"id_evento": ide, "papel": "C", "u": v, "uasg": uv, "cnpj": cv_, "z": z, "w": w,
                               "a": np.nan, "grupo": grupo, "celula": cel, "t0": int(t0), "direcao": r0.direcao})
    L = pd.DataFrame(linhas)
    if len(L) and pesos in ("inv_eventos_uasg", "orgao"):
        T = L.papel == "T"
        campo = "uasg" if pesos == "inv_eventos_uasg" else "cnpj"
        cont = L[T].groupby(campo).id_evento.nunique()
        L.loc[T, "a"] = 1.0 / L.loc[T, campo].map(cont)
    return L


def taus_evento(linhas):
    from .inferencia import eventos_tau
    return eventos_tau(linhas) if len(linhas) else pd.DataFrame()
