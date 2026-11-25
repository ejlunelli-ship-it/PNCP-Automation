"""Etapa 2: painel UASG × trimestre da S1.

Fontes (somente leitura):
- pncp_v2.db: atividade institucional de TODAS as compras A/AF do Pregão Eletrônico (dados abertos): compras, itens,
  classes CATMAT, SRP, sigilo, homologação, fracasso, deserção, esfera, poder, UF. Agregada por UASG × trimestre.
- Amostra S1 da rodada anterior (708.964 itens; índices A1 leave-one-UASG-out já calculados com as regras do
  estudo original, sem nenhuma mudança de aparas, extremos ou mínimos).
- regime_compras.pkl (todas as compras A/AF da fonte; o modo é observado diretamente em cada compra).

O painel guarda os desfechos de TODOS os trimestres; o isolamento entre desenho e estimação é feito pela classe
`PainelPre` (corte estrito antes de t0), única porta de acesso usada pelas etapas da Fase I.
"""
import sqlite3

import numpy as np
import pandas as pd

from . import comum

A, AF, MISTO, NAO_OBS = 0, 1, 2, -1


# ----------------------------------------------------------------------------------------------- extração do banco

def extrair_atividade(c, banco, log):
    """Agregados por compra e por UASG × trimestre × classe CATMAT (todas as compras A/AF eletrônicas)."""
    destino = comum.trabalho(c, "atividade.pkl.gz")
    if destino.exists():
        return destino
    from em.comum import conectar_ro
    con = conectar_ro(banco)                       # URI ?mode=ro + PRAGMA query_only = 1
    con.execute("PRAGMA temp_store = MEMORY")
    filtro = ("c.fonte = 'dados_abertos' AND c.modalidade_nome = 'Pregão - Eletrônico' "
              "AND c.modo_disputa IN ('Aberto', 'Aberto-Fechado') AND c.uasg IS NOT NULL")
    log("extraindo compras A/AF (somente leitura)")
    compras = pd.read_sql_query(f"""SELECT c.numero_controle_pncp AS chave, c.uasg, c.orgao_cnpj, c.esfera, c.poder, c.uf,
        c.modo_disputa, c.srp, c.valor_total_estimado, substr(c.data_abertura_proposta, 1, 10) AS data_abertura
        FROM compras c WHERE {filtro}""", con)
    log(f"{len(compras):,} compras; extraindo itens (registro_principal = 1) por compra × classe")
    partes = []
    q = f"""SELECT c.numero_controle_pncp AS chave, i.codigo_classe AS classe, i.cod_item_catalogo AS catmat,
        i.situacao_item AS sit, i.orcamento_sigiloso AS sig
        FROM compras c JOIN itens i ON i.numero_controle_pncp = c.numero_controle_pncp AND i.registro_principal = 1
        WHERE {filtro}"""
    mapa = {}
    n = 0
    for ch in pd.read_sql_query(q, con, chunksize=1_000_000):
        n += len(ch)
        ch["hom"] = (ch.sit == "Homologado").astype("int32")
        ch["frac"] = (ch.sit == "Fracassado").astype("int32")
        ch["des"] = (ch.sit == "Deserto").astype("int32")
        ch["decid"] = ch.sit.isin(["Homologado", "Fracassado", "Deserto"]).astype("int32")
        ch["sig"] = pd.to_numeric(ch.sig, errors="coerce").fillna(0).astype("int32")
        ch["classe"] = pd.to_numeric(ch.classe, errors="coerce").fillna(-1).astype("int32")
        ch["n"] = 1
        partes.append(ch.groupby(["chave", "classe"], observed=True)[["n", "hom", "frac", "des", "decid", "sig"]].sum()
                      .reset_index())
        m = ch[["catmat", "classe"]].dropna().drop_duplicates()
        for k, v in zip(m.catmat, m.classe):
            mapa.setdefault(int(k), int(v))
        log(f"  {n:,} itens lidos")
    con.close()
    itens = pd.concat(partes).groupby(["chave", "classe"], observed=True).sum().reset_index()
    comum.salvar_pkl(destino, {"compras": compras, "itens_classe": itens, "catmat_classe": mapa, "itens_lidos": n})
    return destino


# ----------------------------------------------------------------------------------------------- painel

class Painel:
    """Arrays U × T (T = trimestres do regime) + tabelas longas. Índice de trimestre j corresponde a t = t_ini + j."""

    def __init__(self, unidades, t_ini, t_fim):
        self.unidades = list(unidades)
        self.pos = {u: i for i, u in enumerate(self.unidades)}
        self.t_ini, self.t_fim = t_ini, t_fim
        self.T = t_fim - t_ini + 1
        self.arr = {}          # nome -> ndarray U × T
        self.attr = {}         # nome -> ndarray U (atributos fixos institucionais)
        self.longo = {}        # nome -> DataFrame com colunas u (int), t (int absoluto), ...

    def j(self, t):
        return int(t) - self.t_ini

    def ate(self, t0):
        return PainelPre(self, t0)


class PainelPre:
    """Visão do painel ESTRITAMENTE anterior a t0 (colunas t < t0). Qualquer acesso a t >= t0 levanta erro.
    A única informação contemporânea liberada é o regime de modo em t0 (`status_t0`), que define tratamento e
    risco; nenhum preço, quantidade ou disponibilidade de preço de t >= t0 é exposto."""

    def __init__(self, p, t0):
        self._p, self.t0 = p, int(t0)
        self.unidades, self.pos, self.t_ini = p.unidades, p.pos, p.t_ini
        self.attr = p.attr
        k = self.t0 - p.t_ini
        self._k = k
        self.arr = {n: a[:, :max(k, 0)].copy() for n, a in p.arr.items()}
        self.longo = {n: d[d.t < self.t0] for n, d in p.longo.items()}
        self.status_t0 = p.arr["status"][:, k].copy() if 0 <= k < p.T else np.full(len(p.unidades), NAO_OBS)

    def col(self, nome, t):
        t = int(t)
        if t >= self.t0:
            raise comum.ErroDesenho(f"acesso a {nome} em t={t} >= t0={self.t0} na Fase I")
        j = t - self.t_ini
        if j < 0:
            return np.full(len(self.unidades), np.nan if nome != "status" else NAO_OBS)
        return self.arr[nome][:, j]

    def janela(self, nome, rel_ini, rel_fim):
        """Colunas t0+rel_ini .. t0+rel_fim (inclusive), rel_fim < 0."""
        return np.column_stack([self.col(nome, self.t0 + r) for r in range(rel_ini, rel_fim + 1)])


def status_regime(reg):
    g = reg.groupby(["uasg", "tri"], observed=True).af.agg(["size", "sum"]).reset_index()
    g.columns = ["uasg", "tri", "n", "n_af"]
    g["status"] = np.where(g.n_af == 0, A, np.where(g.n_af == g.n, AF, MISTO))
    return g


def _media_compra(d, col):
    """Item -> compra (peso igual) -> UASG × trimestre (peso igual por compra)."""
    pc = d.groupby(["uasg", "tri", "chave"], observed=True)[col].mean().reset_index()
    return pc.groupby(["uasg", "tri"], observed=True)[col].agg(["mean", "size"]).reset_index()


def referencia_estaveis_local(pool, status_long, min_itens=5, min_uasgs=3):
    """A1 só com UASGs comparadoras de regime local estável: inequívoco em t e igual ao de t−1 (inequívoco).
    Mesma fórmula leave-one-UASG-out (vetorizada) da referência EST_A1 do estudo original; só muda o conjunto."""
    from em.inferencia import codificar
    st = status_long.set_index(["uasg", "tri"]).status
    s_t = st.reindex(list(zip(pool.uasg, pool.tri))).to_numpy()
    s_tm1 = st.reindex(list(zip(pool.uasg, pool.tri - 1))).to_numpy()
    est = (np.isin(s_t, [A, AF]) & (s_t == s_tm1)).astype(float)
    cell = codificar(pool["produto"].astype(str).to_numpy(), pool["tri"].to_numpy())
    unit = codificar(pool["uasg"].astype(str).to_numpy())
    cu = codificar(cell, unit)
    lp = pool["logp"].to_numpy(float)
    Gc, Gcu = cell.max() + 1, cu.max() + 1
    cell_of_cu = np.zeros(Gcu, dtype=np.int64)
    cell_of_cu[cu] = cell
    n_cs = np.bincount(cell, weights=est, minlength=Gc)
    sl_cs = np.bincount(cell, weights=lp * est, minlength=Gc)
    n_cus = np.bincount(cu, weights=est, minlength=Gcu)
    sl_cus = np.bincount(cu, weights=lp * est, minlength=Gcu)
    est_cu = np.zeros(Gcu)
    est_cu[cu] = est
    k_cs = np.bincount(cell_of_cu, weights=est_cu, minlength=Gc)
    n_os = n_cs[cell] - n_cus[cu]
    k_os = k_cs[cell] - est_cu[cu]
    ok = (n_os >= min_itens) & (k_os >= min_uasgs)
    with np.errstate(divide="ignore", invalid="ignore"):
        ref = np.where(ok, (sl_cs[cell] - sl_cus[cu]) / n_os, np.nan)
    return pd.Series(100 * (lp - ref), index=pool.index), est


def construir(c, dados_dir, ativ_path, log, nome="S1"):
    from em.descritivas import base_principal
    dados_dir = comum.resolver(dados_dir)
    am = pd.read_pickle(dados_dir / "amostra.pkl")
    idx = pd.read_pickle(dados_dir / "indices.pkl")
    reg = pd.read_pickle(dados_dir / "regime_compras.pkl")
    reg["uasg"] = reg.uasg.astype(str).str.strip().str.zfill(6)
    per = c["periodo"]
    t_ini, t_fim = comum.tri(per["regime_primeiro"]), comum.tri(per["regime_ultimo"])
    reg = reg[reg.tri.notna() & (reg.tri >= t_ini) & (reg.tri <= t_fim)].copy()
    reg["tri"] = reg.tri.astype(int)
    st = status_regime(reg)
    base = base_principal(am, idx)
    # referência original (cesta candidata) e referência local de UASGs estáveis
    ic = pd.read_pickle(comum.resolver(c["fontes"]["dados_cesta"]) / "indices.pkl")
    base["y_A1_cesta"] = ic["y_A1"].reindex(base.index).where(ic["mascara_A1"].reindex(base.index).fillna(False).astype(bool))
    del ic
    pool = am.loc[am.elegivel_preco, ["produto", "tri", "uasg", "logp"]].copy()
    pool["uasg"] = pool.uasg.astype(str)
    pool["tri"] = pool.tri.astype(int)
    yl, _ = referencia_estaveis_local(pool, st)
    lim = 100 * comum.ler_json(comum.ORIGINAL / "config.json")["referencia"]["extremo_ln"]
    base["y_ESTL_A1"] = yl.reindex(base.index).where(lambda s: s.abs() <= lim)
    base["y_EST_A1"] = base["y_EST_A1"].where(base["propria_EST_A1"])
    t_p0, t_p1 = comum.tri(per["preco_primeiro"]), comum.tri(per["preco_ultimo"])
    base = base[(base.tri >= t_p0) & (base.tri <= t_p1)].copy()
    # unidades: todas as UASGs com compras A/AF no período
    unidades = sorted(set(reg.uasg))
    P = Painel(unidades, t_ini, t_fim)
    U, T = len(unidades), P.T
    pos = P.pos

    def matriz(df, col, preencher=np.nan, dtype=float):
        M = np.full((U, T), preencher, dtype=dtype)
        r = df.uasg.map(pos).to_numpy()
        k = (df.tri.astype(int) - t_ini).to_numpy()
        ok = ~pd.isna(r) & (k >= 0) & (k < T)
        M[r[ok].astype(int), k[ok]] = df[col].to_numpy()[ok]
        return M

    P.arr["status"] = matriz(st, "status", NAO_OBS, np.int8)
    P.arr["n_compras_modo"] = matriz(st, "n", 0.0)
    P.arr["n_af_modo"] = matriz(st, "n_af", 0.0)
    # desfechos (índice): compra-média (principal) e item-média, para cada referência
    for ycol, sufixo in (("y_A1", ""), ("y_A1_cesta", "_cesta"), ("y_EST_A1", "_estg"), ("y_ESTL_A1", "_estl")):
        d = base[base[ycol].notna()]
        g = _media_compra(d, ycol)
        P.arr[f"Yc{sufixo}"] = matriz(g, "mean")
        P.arr[f"nC{sufixo}"] = matriz(g, "size", 0.0)
        gi = d.groupby(["uasg", "tri"], observed=True)[ycol].agg(["mean", "size"]).reset_index()
        P.arr[f"Yi{sufixo}"] = matriz(gi, "mean")
        P.arr[f"nI{sufixo}"] = matriz(gi, "size", 0.0)
    # atividade S1 licitada (todos os itens S1 da população, não só homologados)
    pop = am[am.tri.notna()].copy()
    pop["uasg"] = pop.uasg.astype(str)
    pop["tri"] = pop.tri.astype(int)
    g = pop.groupby(["uasg", "tri"], observed=True).agg(n_itens_s1=("chave", "size"), logq_soma=("logq", "sum"),
                                                        logq_n=("logq", "count")).reset_index()
    for col in ("n_itens_s1", "logq_soma", "logq_n"):
        P.arr[col] = matriz(g, col, 0.0)
    # atividade institucional (pncp_v2: todas as compras A/AF eletrônicas)
    at = comum.ler_pkl(ativ_path)
    co = at["compras"].copy()
    co["uasg"] = co.uasg.astype(str).str.strip().str.zfill(6)
    da = pd.to_datetime(co.data_abertura, errors="coerce", format="%Y-%m-%d")
    co["tri"] = (da.dt.year * 4 + (da.dt.month - 1) // 3)
    co = co[co.tri.notna()].copy()
    co["tri"] = co.tri.astype(int)
    co["srp"] = pd.to_numeric(co.srp, errors="coerce").fillna(0)
    co["lv"] = np.log(pd.to_numeric(co.valor_total_estimado, errors="coerce").where(lambda s: s > 0))
    gc = co.groupby(["uasg", "tri"]).agg(n_compras=("chave", "size"), n_srp=("srp", "sum"), lv_soma=("lv", "sum"),
                                         lv_n=("lv", "count")).reset_index()
    for col in ("n_compras", "n_srp", "lv_soma", "lv_n"):
        P.arr[col] = matriz(gc, col, 0.0)
    it = at["itens_classe"].merge(co[["chave", "uasg", "tri"]], on="chave")
    gi = it.groupby(["uasg", "tri"])[["n", "hom", "frac", "des", "decid", "sig"]].sum().reset_index()
    for col in ("n", "hom", "frac", "des", "decid", "sig"):
        P.arr[f"it_{col}"] = matriz(gi, col, 0.0)
    gcl = it.groupby(["uasg", "tri", "classe"]).n.sum().reset_index()
    gcl["u"] = gcl.uasg.map(pos)
    gcl = gcl[gcl.u.notna()].astype({"u": int})
    P.longo["classes"] = gcl.rename(columns={"tri": "t"})[["u", "t", "classe", "n"]].reset_index(drop=True)
    # atributos institucionais fixos (moda em todas as compras; identificadores, não escolhas posteriores)
    moda = lambda s: s.dropna().astype(str).mode().iat[0] if s.notna().any() else ""
    inst = co.groupby("uasg").agg(esfera=("esfera", moda), poder=("poder", moda), uf=("uf", moda))
    cnpj = reg.groupby("uasg").orgao_cnpj.agg(lambda s: s.mode().iat[0])
    for col in ("esfera", "poder", "uf"):
        P.attr[col] = inst[col].reindex(unidades).fillna("").to_numpy()
    P.attr["cnpj"] = cnpj.reindex(unidades).fillna("?").astype(str).to_numpy()
    # tabelas longas S1 (produto e classe CATMAT dos itens com índice; produtos licitados)
    cc = at["catmat_classe"]
    b = base[["uasg", "tri", "chave", "produto", "y_A1"]].copy()
    b["catmat"] = am.loc[b.index, "catmat"].to_numpy()
    b["u"] = b.uasg.map(pos)
    b = b[b.u.notna()]
    b["u"] = b.u.astype(int)
    b["classe"] = b.catmat.map(lambda k: cc.get(int(k), -1)).astype(int)
    P.longo["itens_y"] = b.rename(columns={"tri": "t"})[["u", "t", "chave", "produto", "classe", "y_A1"]].reset_index(drop=True)
    pp = pop.groupby(["uasg", "tri", "produto"], observed=True).size().rename("n").reset_index()
    pp["u"] = pp.uasg.map(pos)
    pp = pp[pp.u.notna()].astype({"u": int})
    P.longo["produtos_licitados"] = pp.rename(columns={"tri": "t"})[["u", "t", "produto", "n"]].reset_index(drop=True)
    # classes CATMAT principais (fixadas pela frequência em TODO o banco A/AF; não dependem de eventos ou preços)
    top = it.groupby("classe").n.sum().sort_values(ascending=False)
    P.attr["_classes_top"] = np.array([k for k in top.index if k >= 0][: c["matching"]["classes_catmat_top"]])
    cob = (base.groupby("tri").agg(itens=("chave", "size"), compras=("chave", "nunique"), uasgs=("uasg", "nunique"),
                                   orgaos=("orgao_cnpj", "nunique"), itens_cesta=("y_A1_cesta", "count"),
                                   itens_estg=("y_EST_A1", "count"), itens_estl=("y_ESTL_A1", "count"))
           .reset_index())
    cob["trimestre"] = cob.tri.map(comum.nome_tri)
    resumo = {"amostra": nome, "unidades_regime": U, "trimestres_regime": f"{per['regime_primeiro']}–{per['regime_ultimo']}",
              "trimestres_preco": f"{per['preco_primeiro']}–{per['preco_ultimo']}", "itens_com_indice": int(len(base)),
              "compras_com_indice": int(base.chave.nunique()), "produtos_com_indice": int(base.produto.nunique()),
              "uasgs_com_indice": int(base.uasg.nunique()), "cnpjs_com_indice": int(base.orgao_cnpj.nunique()),
              "itens_amostra": int(len(am)), "compras_amostra": int(am.chave.nunique()),
              "uasg_trimestres_observados": int(len(st)), "uasg_trimestres_mistos": int((st.status == MISTO).sum()),
              "compras_regime": int(len(reg)), "compras_atividade_pncp": int(len(co)), "itens_atividade_pncp": int(at["itens_lidos"])}
    return P, cob, resumo
