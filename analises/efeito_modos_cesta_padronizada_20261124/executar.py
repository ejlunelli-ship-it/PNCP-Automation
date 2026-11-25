"""Estudo econométrico A × AF na cesta padronizada — comando único (ver protocolo.md e metodologia.md).

    python executar.py                         # todas as etapas, na ordem do protocolo
    python executar.py --etapas amostra        # uma ou mais etapas (vírgulas)

Etapas (ordem do pedido, §16):
  validar       1. conjunto de produtos efetivamente aprovado; interseções da cesta
  amostra       2. amostra de preços (pncp_v2.db, só leitura), auditoria das chaves e funil
  cobertura     3. cobertura temporal e identificação dos eventos (regime por UASG × trimestre)
  referencias   5. referências leave-one-UASG-out A1–A5, B1–B9 e estáveis; índices
  descritivas   6. estatísticas por modo e diferença bruta com inferência agrupada
  efeitos_fixos 7. painel de efeitos fixos (associação condicional)
  eventos       8. estudo de eventos dCDH (reversível) + BJS (subconjunto absorvente)
  honestdid     9. HonestDiD (R) com a covariância de cada especificação
  robustez     10. referências, ponderações, amostras e janelas
  secundarios  11. desconto, homologação, fracasso, deserção, seleção
  relatorio    13. relatorio.md, conclusao.md, registro_execucao.json
(4. o protocolo é fixado antes, em protocolo.md; 12. testes: python -m unittest discover -s testes)

A análise principal exige produtos aprovados. Sem eles, TODAS as estimativas saem marcadas como exploratórias.
"""
import argparse
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from em import VERSAO, comum  # noqa: E402

ETAPAS = ["validar", "amostra", "cobertura", "referencias", "descritivas", "efeitos_fixos", "eventos", "honestdid",
          "robustez", "secundarios", "relatorio"]


def principal(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--etapas", default=",".join(ETAPAS))
    ap.add_argument("--config", default=str(AQUI / "config.json"))
    ap.add_argument("--v2")
    ap.add_argument("--cesta-trabalho")
    ap.add_argument("--cesta-pasta")
    ap.add_argument("--trabalho")
    ap.add_argument("--saidas", default=str(AQUI))
    ap.add_argument("--bootstrap", type=int, help="sobrescreve o nº de réplicas (testes)")
    a = ap.parse_args(argv)
    etapas = [e.strip() for e in a.etapas.split(",") if e.strip()]
    for e in etapas:
        if e not in ETAPAS:
            ap.error(f"etapa desconhecida: {e}")
    cfg = comum.carregar_config(a.config)
    if a.bootstrap:
        cfg["efeitos_fixos"]["bootstrap_wcr"] = a.bootstrap
        cfg["eventos"]["bootstrap"] = a.bootstrap
    cam = comum.resolver(cfg, pncp_v2=a.v2, cesta_trabalho=a.cesta_trabalho, cesta_pasta=a.cesta_pasta, trabalho=a.trabalho)
    saidas = Path(a.saidas)
    ctx = {"cfg": cfg, "cam": cam, "saidas": saidas, "reg": comum.Registro(), "config_arquivo": Path(a.config),
           "trabalho_db": cam["trabalho"] / "trabalho.db", "dados": cam["trabalho"]}
    from em import pipeline
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S")
    for e in ETAPAS:
        if e in etapas:
            getattr(pipeline, "etapa_" + e)(ctx)
    comum.escrever_json(saidas / "registros" / f"execucao_{'-'.join(etapas)}.json",
                        {"versao": VERSAO, "inicio": t0, "fim": time.strftime("%Y-%m-%dT%H:%M:%S"), "etapas": ctx["reg"].etapas,
                         "contagens": ctx["reg"].contagens, "avisos": ctx["reg"].avisos})
    print("concluído")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
