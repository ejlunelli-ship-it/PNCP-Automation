"""Interface única da validação técnica da cesta padronizada.

    python scripts/executar.py inspect
    python scripts/executar.py preparar --prioridade P1 --limite 100     # piloto  -> saidas/piloto_P1_100/
    python scripts/executar.py preparar --prioridade P1                  # todos P1 -> saidas/P1/
    python scripts/executar.py concluir --exigir-dupla-revisao           # rodada padrão (P1); --rodada para outra
    python scripts/executar.py testes                                    # roda a suíte e grava saidas/resultado_testes.json
    python scripts/executar.py relatorio                                 # relatorio.md e manifesto.json da raiz

Entradas só em leitura (CSV) e mode=ro (SQLite). Nenhuma etapa lê preço, valor, desconto, modo de disputa,
licitantes ou resultado econométrico. Nenhuma etapa preenche decisões.
"""
import argparse
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comum  # noqa: E402
from comum import ErroEstrutural  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="pasta de configuração (padrão: config/)")
    sub = ap.add_subparsers(dest="comando", required=True)
    sub.add_parser("inspect", help="inspeciona as entradas e confere o mapeamento de colunas")
    p = sub.add_parser("preparar", help="gera arquivos-base, auditoria e formulários de uma rodada")
    p.add_argument("--prioridade", default="P1", help="P1…P5 ou 'todas'")
    p.add_argument("--limite", type=int, help="só os N primeiros na ordem de revisão (piloto)")
    p.add_argument("--saida", help="pasta da rodada (padrão: saidas/<rodada>)")
    c = sub.add_parser("concluir", help="valida os formulários preenchidos e emite o resultado")
    c.add_argument("--rodada", help="pasta ou nome da rodada (padrão: parametros.rodada_padrao)")
    c.add_argument("--exigir-dupla-revisao", action="store_true", help="aprovador final ≠ revisores das variantes")
    sub.add_parser("testes", help="executa testes/test_validacao.py e grava o resultado")
    sub.add_parser("relatorio", help="gera relatorio.md e manifesto.json a partir das rodadas")
    a = ap.parse_args(argv)

    cfg = comum.carregar_config(a.config)
    reg = comum.Registro()
    t0 = time.time()
    try:
        if a.comando == "inspect":
            from inspecionar_entradas import inspecionar
            rel = inspecionar(cfg, reg)
            print(json.dumps(rel["cesta"], ensure_ascii=False, indent=1)[:1500])
        elif a.comando == "preparar":
            from preparar_revisao import preparar
            preparar(cfg, reg, a.prioridade, a.limite, a.saida)
        elif a.comando == "concluir":
            from validar_revisao import concluir
            nome = a.rodada or cfg["parametros"]["rodada_padrao"]
            pasta = Path(nome) if Path(nome).is_dir() else comum.resolver(cfg["parametros"]["saidas"]) / nome
            out = concluir(cfg, reg, pasta, a.exigir_dupla_revisao)
            print(json.dumps({k: v for k, v in out.items() if not k.startswith("hashes")}, ensure_ascii=False, indent=1))
        elif a.comando == "testes":
            return rodar_testes(cfg)
        elif a.comando == "relatorio":
            from relatorio import gerar
            gerar(cfg, reg)
    except ErroEstrutural as e:
        print(f"ERRO ESTRUTURAL: {e}", file=sys.stderr)
        return 2
    reg.log(f"{a.comando} concluído em {time.time() - t0:.1f} s")
    return 0


def rodar_testes(cfg):
    pasta = comum.PASTA / "testes"
    sys.path.insert(0, str(pasta))
    suite = unittest.defaultTestLoader.discover(str(pasta), pattern="test_*.py", top_level_dir=str(pasta))
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    falhas = [{"teste": str(t), "tipo": "falha", "detalhe": d[-2000:]} for t, d in res.failures] + \
             [{"teste": str(t), "tipo": "erro", "detalhe": d[-2000:]} for t, d in res.errors]
    out = {"executado_em": comum.agora(), "testes_executados": res.testsRun, "falhas": len(res.failures), "erros": len(res.errors),
           "ignorados": len(res.skipped), "aprovados": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped),
           "sucesso": res.wasSuccessful(), "detalhes": falhas, "python": sys.version.split()[0]}
    comum.escrever_json(comum.resolver(cfg["parametros"]["saidas"]) / "resultado_testes.json", out)
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
