"""Orquestração. Cada etapa grava em `tabelas/` e no diretório de dados (fora do git)."""
import json
import pickle

from . import comum


def _salvar(ctx, nome, obj):
    p = ctx["dados"] / f"{nome}.pkl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)


def _abrir(ctx, nome):
    with open(ctx["dados"] / f"{nome}.pkl", "rb") as f:
        return pickle.load(f)


def etapa_validar(ctx):
    from . import amostra
    with ctx["reg"].etapa("validar produtos aprovados e conjuntos da cesta"):
        res, conj = amostra.validar_cesta(ctx["cam"], ctx["reg"], ctx["saidas"])
        ctx["reg"].contar("validacao", res)
        _salvar(ctx, "conjuntos", conj)


def etapa_amostra(ctx):
    from . import amostra
    impr = amostra.extrair(ctx["cam"], ctx["cfg"], ctx["reg"], ctx["trabalho_db"])
    comum.escrever_json(ctx["saidas"] / "tabelas" / "impressoes_digitais.json", impr)
    with ctx["reg"].etapa("amostra em memória e funil"):
        df, reg_c = amostra.carregar(ctx["trabalho_db"], ctx["cfg"])
        conj = _abrir(ctx, "conjuntos")
        df = df.merge(conj[["produto", "rigoroso", "aprovado", "recorrente", "inconsistencia_tecnica"]], on="produto", how="left")
        linhas, masks = amostra.funil(df, ctx["cfg"], conj)
        comum.escrever_csv(ctx["saidas"] / "funil_amostra.csv", linhas)
        df["elegivel_preco"] = masks["6_preco_positivo"].to_numpy()
        df["elegivel_principal"] = masks["7_produto_aprovado"].to_numpy()
        df["populacao_desfecho"] = masks["4_data_abertura_valida"].to_numpy()
        _salvar(ctx, "amostra", df)
        _salvar(ctx, "regime_compras", reg_c)
        df.to_csv(ctx["dados"] / "amostra_analitica.csv.gz", index=False, compression="gzip")
        ctx["reg"].contar("funil", linhas)


def etapa_cobertura(ctx):
    from . import eventos
    eventos.cobertura_e_eventos(ctx, _abrir(ctx, "amostra"), _abrir(ctx, "regime_compras"), _salvar)


def etapa_referencias(ctx):
    from . import referencias
    referencias.executar(ctx, _abrir, _salvar)


def etapa_descritivas(ctx):
    from . import descritivas
    descritivas.executar(ctx, _abrir)


def etapa_efeitos_fixos(ctx):
    from . import painel
    painel.executar(ctx, _abrir, _salvar)


def etapa_eventos(ctx):
    from . import eventos
    eventos.executar(ctx, _abrir, _salvar)


def etapa_honestdid(ctx):
    from . import honest
    honest.executar(ctx, _abrir)


def etapa_robustez(ctx):
    from . import robustez
    robustez.executar(ctx, _abrir, _salvar)


def etapa_secundarios(ctx):
    from . import secundarios
    secundarios.executar(ctx, _abrir, _salvar)


def etapa_relatorio(ctx):
    from . import relatorio
    relatorio.executar(ctx, _abrir)
