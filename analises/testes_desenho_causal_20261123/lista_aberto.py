"""Lista das compras do modo Aberto a baixar para o desenho intraleilão (parecer §4.2, protocolo §8).

Prioridade 1: compras Aberto das unidades que mudaram de modo, na janela de ±6 meses do evento (eventos do estudo).
Prioridade 2: as mesmas unidades, de 7 a 12 meses antes ou depois do evento.
Prioridade 3: amostra de unidades estáveis no Aberto (2 controles limpos sorteados por evento A->AF), ±6 meses.
Mês da compra = primeiro mês de resultado dos itens homologados (regra do projeto). Só leitura do pncp.db.

Uso (da pasta PNCP-Automation):
    python analises/testes_desenho_causal_20261123/lista_aberto.py --pncp-db ../dados/pncp.db
Saída: lista_aberto/compras_aberto.csv, lista_aberto/compras_por_mes/<AAAA-MM>.csv (formato de registro/compras/),
lista_aberto/resumo.json.
"""
import argparse, json
from pathlib import Path

import numpy as np
import pandas as pd

import comum as C
import motor as Mo
from poder import carregar, eventos_validos

CAMPOS_COMPRA = ["numeroControlePNCP", "idCompra", "numeroCompra", "anoCompraPncp", "objetoCompra",
                 "dataPublicacaoPncp", "dataAberturaPropostaPncp", "orgaoEntidadeCnpj"]


def campos(alvo, pncp_db):
    sig = C.assinatura(pncp_db)
    con = C.ro(pncp_db)
    con.execute("create temp table alvo(numero_controle_pncp text primary key)")
    con.executemany("insert into temp.alvo values (?)", [(c,) for c in sorted(alvo)])
    c = pd.read_sql_query(
        """select c.numero_controle_pncp as numeroControlePNCP, c.id_compra as idCompra, c.numero_compra as numeroCompra,
                  c.ano_compra as anoCompraPncp, c.objeto_compra as objetoCompra, c.data_publicacao as dataPublicacaoPncp,
                  c.data_abertura_proposta as dataAberturaPropostaPncp, c.orgao_cnpj as orgaoEntidadeCnpj
           from temp.alvo a join compras c on c.numero_controle_pncp = a.numero_controle_pncp""", con)
    m = pd.read_sql_query(
        """select i.numero_controle_pncp as numeroControlePNCP, min(substr(i.data_resultado, 1, 7)) as mes,
                  count(*) as itens_homologados
           from temp.alvo a join itens i on i.numero_controle_pncp = a.numero_controle_pncp
           where i.registro_principal = 1 and i.homologado = 1 group by 1""", con)
    con.close()
    assert C.assinatura(pncp_db) == sig, "pncp.db mudou"
    return c.merge(m, on="numeroControlePNCP", how="left")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pncp-db", type=Path, required=True)
    a = ap.parse_args(argv)
    pn, un, ev = carregar()
    esp = json.loads((C.AQUI / "especificacao.json").read_text(encoding="utf-8"))
    e = eventos_validos(ev, esp["W"])
    res, ctrl = Mo.did_eventos(pn, e, y="e", W=esp["W"], cmin=esp["cmin"], unid=un, ev_todos=ev, guardar_controles=True,
                               perfil=False, cego=True)
    comp = pd.read_pickle(C.DADOS / "compras.pkl")[["compra", "u", "m", "af"]]
    rng = np.random.default_rng(20261123)
    partes = []
    for _, r in res.iterrows():
        u, m = int(r.u), int(r.m)
        z = comp[(comp.u == u) & comp.af.eq(0) & (comp.m >= m - 12) & (comp.m < m + 12)].copy()
        z["prioridade"] = np.where((z.m >= m - 6) & (z.m < m + 6), 1, 2)
        z["papel"] = "unidade que mudou (" + r.tipo + ")"
        z["evento_mes"] = C.mes_str(C.M0 + m)
        partes.append(z)
        if r.tipo == "A->AF":
            cand = ctrl[r.k].u.to_numpy()
            for v in rng.choice(cand, size=min(2, len(cand)), replace=False):
                z = comp[(comp.u == v) & comp.af.eq(0) & (comp.m >= m - 6) & (comp.m < m + 6)].copy()
                z["prioridade"] = 3
                z["papel"] = "controle estável no Aberto"
                z["evento_mes"] = C.mes_str(C.M0 + m)
                partes.append(z)
    lista = pd.concat(partes).sort_values("prioridade").drop_duplicates("compra")
    info = campos(lista.compra.astype(str), a.pncp_db)
    lista["numeroControlePNCP"] = lista.compra.astype(str)
    lista = lista.merge(info, on="numeroControlePNCP", how="left")
    lista["objetoCompra"] = lista.objetoCompra.fillna("").map(lambda x: " ".join(x.split())[:100])
    lista["uasg"] = un.unidade.reindex(lista.u).to_numpy()
    lista = lista[lista.mes.notna()].sort_values(["prioridade", "mes", "numeroControlePNCP"])
    pasta = C.AQUI / "lista_aberto"
    (pasta / "compras_por_mes").mkdir(parents=True, exist_ok=True)
    for f in (pasta / "compras_por_mes").glob("*.csv"):
        f.unlink()
    cols = ["prioridade", "mes", "papel", "evento_mes", "uasg"] + CAMPOS_COMPRA + ["itens_homologados"]
    lista[cols].to_csv(pasta / "compras_aberto.csv", index=False, encoding="utf-8", lineterminator="\n")
    for mes, g in lista.groupby("mes"):
        g.sort_values("numeroControlePNCP")[CAMPOS_COMPRA].to_csv(pasta / "compras_por_mes" / f"{mes}.csv", index=False,
                                                                   encoding="utf-8", lineterminator="\n")
    resumo = {"eventos": res.tipo.value_counts().to_dict(),
              "por_prioridade": {int(p): {"compras": int(len(g)), "itens_homologados": int(g.itens_homologados.sum()),
                                          "unidades": int(g.u.nunique()), "sem_idCompra": int(g.idCompra.isna().sum())}
                                 for p, g in lista.groupby("prioridade")},
              "meses": [lista.mes.min(), lista.mes.max()], "sem_resultado_excluidas": "compras sem item homologado"}
    (pasta / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=1, default=float))
    print("FIM ok")


if __name__ == "__main__":
    main()
