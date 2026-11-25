"""Gera cesta_validada.csv a partir do formulário de revisão preenchido por um revisor humano.

    python validar_revisao.py [--formulario saidas/formulario_revisao.csv] [--saida saidas/cesta_validada.csv]

Só entra na cesta validada a linha com decisão 'aprovar' e TODOS os campos obrigatórios preenchidos
(especificação canônica, atributos essenciais, critérios de equivalência e de exclusão, revisor, data
no formato AAAA-MM-DD e justificativa). Linhas incompletas são listadas e recusadas. O script nunca
preenche aprovação: sem revisão, a cesta validada fica vazia (pendente).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DECISAO = "decisao (aprovar/rejeitar/dividir)"
OBRIGATORIOS = ["especificacao_canonica_aprovada", "atributos_essenciais", "criterios_equivalencia",
                "criterios_exclusao", "revisor", "data_revisao", "justificativa"]
SAIDA_COLS = ["id_candidato", "produto", "catmat", "unidade_norm", "especificacao_canonica_aprovada",
              "atributos_essenciais", "criterios_equivalencia", "criterios_exclusao", "revisor", "data_revisao",
              "justificativa", "versao_regra_classificacao"]


def validar(linhas):
    aprovadas, recusadas = [], []
    for r in linhas:
        dec = (r.get(DECISAO) or "").strip().lower()
        if dec != "aprovar":
            if dec:
                recusadas.append({"id_candidato": r.get("id_candidato"), "motivo": f"decisão '{dec}'"})
            continue
        faltam = [c for c in OBRIGATORIOS if not (r.get(c) or "").strip()]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", (r.get("data_revisao") or "").strip()):
            faltam.append("data_revisao (AAAA-MM-DD)")
        if faltam:
            recusadas.append({"id_candidato": r.get("id_candidato"), "motivo": "campos ausentes: " + ", ".join(faltam)})
            continue
        aprovadas.append({c: (r.get(c) or "").strip() for c in SAIDA_COLS})
    return aprovadas, recusadas


def principal(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--formulario", default=str(AQUI / "saidas" / "formulario_revisao.csv"))
    ap.add_argument("--saida", default=str(AQUI / "saidas" / "cesta_validada.csv"))
    a = ap.parse_args(argv)
    with open(a.formulario, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    aprovadas, recusadas = validar(linhas)
    with open(a.saida, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, SAIDA_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(aprovadas)
    rel = {"formulario": a.formulario, "linhas": len(linhas), "aprovadas": len(aprovadas), "recusadas": recusadas,
           "situacao": "PENDENTE: nenhuma aprovação registrada" if not aprovadas else "parcial/concluída pela revisão"}
    Path(a.saida).with_name("validacao_revisao.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in rel.items() if k != "recusadas"}, ensure_ascii=False), f"recusadas: {len(recusadas)}")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
