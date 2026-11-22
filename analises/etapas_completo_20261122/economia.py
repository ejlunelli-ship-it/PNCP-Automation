"""Economia em R$ atribuível à 2ª etapa e descontos ponderados pelo valor, na base completa 1.9.1 (AF e FA).

Mesma amostra do analise_etapas.py (ler_bancos/preparar; regra do mês = primeiro mês do resultado), duas medidas
(todos os fornecedores; só válidos). Quantidade = valor_estimado_total / valor_estimado (unitário); itens sem
valor total positivo ficam fora. Economia da 2ª etapa = (melhor valor da 1ª etapa − melhor após a 2ª) × quantidade.
Descontos ponderados = 1 − Σ(valor × quantidade) / Σ estimado total. Agregação em float (relato), não em Decimal.

Uso (da pasta PNCP-Automation):
    python analises/etapas_completo_20261122/economia.py --db dados/extracao/aberto-fechado_parser-1.9.1.db \
        --saida dados/analise_etapas/completo_20261122
Saída: <saida>/economia.json (e na tela).
"""
import argparse, json, sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import analise_etapas as ae  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--saida", type=Path, required=True)
    a = ap.parse_args(argv)
    R = {}
    for modo in ["aberto-fechado", "fechado-aberto"]:
        e = ae.MODOS[modo]
        df, _ = ae.preparar(ae.ler_bancos([a.db], None, e), e)
        s = df[df.na_amostra]
        del df
        R[modo] = {}
        for nome, suf in [("todos os fornecedores", ""), ("só fornecedores válidos", "_v")]:
            d = s if suf == "" else s[s.validos_ok]
            p1 = d[e["c1"]] if suf == "" else d[e["c1v"]]
            apos = d.melhor_apos if suf == "" else d.apos_v
            q = (d.valor_estimado_total / d.valor_estimado).where(d.valor_estimado_total > 0)
            m = q.notna()
            p1, apos, q, est, fin = p1[m], apos[m], q[m], d.valor_estimado_total[m], d.valor_final[m]
            tot_est, tot1, tot_ap = float(est.sum()), float((p1 * q).sum()), float((apos * q).sum())
            mf = fin.notna()
            eco = tot1 - tot_ap
            # concentração: parcela da economia nos 1% de itens com maior economia
            eco_i = ((p1 - apos) * q).to_numpy()
            top = np.sort(eco_i)[::-1][: max(1, len(eco_i) // 100)].sum()
            R[modo][nome] = {
                "itens": int(m.sum()), "valor_estimado_total_R$": tot_est, f"total_melhor_{e['rot1']}_R$": tot1,
                f"total_apos_{e['rot2']}_R$": tot_ap, f"economia_{e['rot2']}_R$": eco,
                f"economia_{e['rot2']}_pct_do_{e['rot1']}": 100 * eco / tot1,
                f"desconto_ponderado_{e['rot1']}": 100 * (1 - tot1 / tot_est),
                f"desconto_ponderado_apos_{e['rot2']}": 100 * (1 - tot_ap / tot_est),
                "desconto_ponderado_final": 100 * (1 - float((fin[mf] * q[mf]).sum()) / float(est[mf].sum())),
                "itens_com_final": int(mf.sum()),
                "parcela_economia_top1pct_itens": float(top / eco) if eco else None}
        del s
    a.saida.mkdir(parents=True, exist_ok=True)
    (a.saida / "economia.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
