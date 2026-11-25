"""Gera relatorio.md e manifesto.json (raiz) a partir das saídas das rodadas. Nenhum número é digitado à mão,
e nenhum preço, valor, desconto ou modo de disputa é lido."""
import json
from collections import Counter
from pathlib import Path

import comum

RODADAS = ("piloto_P1_100", "P1")


def _n(x):
    return f"{int(x):,}".replace(",", ".")


def _pct(a, b):
    return f"{100 * a / b:.1f}%".replace(".", ",") if b else "—"


def _tab(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in l) + " |" for l in linhas]
    return "\n".join(out)


def gerar(cfg, reg):
    saidas = comum.resolver(cfg["parametros"]["saidas"])
    pasta = comum.PASTA
    insp = comum.carregar_json(saidas / "inspecao_entradas.json")
    testes = comum.carregar_json(saidas / "resultado_testes.json") if (saidas / "resultado_testes.json").exists() else None
    rod = {}
    for r in RODADAS:
        p = saidas / r
        if not (p / "manifesto.json").exists():
            continue
        rod[r] = {"pasta": p, "man": comum.carregar_json(p / "manifesto.json"),
                  "res": comum.carregar_json(p / "resultado_validacao.json") if (p / "resultado_validacao.json").exists() else None,
                  "prod": list(comum.ler_csv(p / "base_produtos.csv")), "var": list(comum.ler_csv(p / "base_variantes.csv")),
                  "conf": list(comum.ler_csv(p / "auditoria_conflitos.csv"))}
    P1 = rod["P1"]
    prods = [p for p in P1["prod"] if p["tipo_registro"] == "PRODUTO"]
    subs = [p for p in P1["prod"] if p["tipo_registro"] == "SUBPRODUTO"]
    V = P1["var"]
    m = P1["man"]
    n = len(prods)
    vpp = Counter(Counter(v["id_candidato"] for v in V).values())
    itens_v = sorted(int(v["itens"]) for v in V)
    raras1 = sum(1 for x in itens_v if x <= 1)
    raras5 = sum(1 for x in itens_v if x <= 5)
    sem_desc = sum(1 for v in V if v["descricao_ausente"] == "1")
    st = Counter(p["status_auditoria"] for p in prods)
    so_decl = sum(1 for p in prods if all(json.loads(v["atributos"]) == {} for v in V if v["id_candidato"] == p["id_candidato"]
                                         and v["descricao_ausente"] != "1"))
    conf_obj = Counter((c["atributo"], c["id_candidato"]) for c in P1["conf"] if c["gravidade"] == "OBJETIVO")
    tipos_obj = Counter(a for a, _ in conf_obj)
    conf_ex = {(c["atributo"].split(":")[0] if c["atributo"].startswith("declarado:") else c["atributo"], c["id_candidato"])
               for c in P1["conf"] if c["gravidade"] == "A_EXAMINAR"}
    tipos_ex = Counter(a for a, _ in conf_ex)
    esp = Counter(r for p in prods for r in p["requer_especialista"].split(";") if r)
    edital = Counter(x.split(":")[0] for p in prods for x in p["consulta_edital"].split(" | ") if x)
    n_edital = sum(1 for p in prods if p["consulta_edital"])
    res = P1["res"] or {}
    val = [r for r in comum.ler_csv(P1["pasta"] / "resultado_revisao.csv") if r["status_final"] == "VALIDADO"] \
        if (P1["pasta"] / "resultado_revisao.csv").exists() else []
    comp_tot = sum(int(p["compras"]) for p in prods)
    cand = insp["cesta"]
    pri = m["priorizacao_total"]

    L = []
    L.append("# Validação técnica da cesta padronizada — relatório\n")
    L.append(f"Gerado em {comum.agora()} por `scripts/executar.py relatorio` (versão {comum.VERSAO}). Protocolo: "
             "[`protocolo_validacao.md`](protocolo_validacao.md); método: [`metodologia_validacao.md`](metodologia_validacao.md); "
             "conclusão: [`conclusao.md`](conclusao.md).\n")
    L.append("> **Nenhum produto está validado.** A auditoria automática examinou 100% das descrições dos candidatos P1 e "
             "preparou os formulários; nenhuma decisão humana documentada foi registrada, então `cesta_validada.csv` **não foi criada** "
             "e a prioridade P1 **não** equivale a aprovação. A auditoria não leu preço, valor, desconto, modo de disputa, licitantes "
             "nem resultado econométrico.\n")
    L.append("## Entradas e identificação dos produtos\n")
    L.append(_tab(["Conjunto", "Produtos"], [
        ["Cesta candidata", _n(cand["candidatos"])], ["Classe A", _n(cand["classe_A"])], ["Classe B", _n(cand["classe_B"])],
        ["Famílias do cenário rigoroso", _n(cand["familias_rigoroso"])], ["Candidatos nessas famílias", _n(cand["candidatos_em_familias_rigoroso"])],
        ["**P1 = A ∩ rigoroso**", f"**{_n(pri.get('P1', 0))}**"], ["P2 = A fora do rigoroso", _n(pri.get("P2", 0))],
        ["P3 = B ∩ rigoroso", _n(pri.get("P3", 0))], ["P4 = B fora do rigoroso", _n(pri.get("P4", 0))], ["P5 = demais", _n(pri.get("P5", 0))]]))
    L.append("\n- Chave do produto: `produto` = `catmat|unidade_norm` (com sufixo `#hash` em 3 subtipos já separados pela cesta); "
             "identificador estável: `id_candidato`. Descrição → produto: (`familia`, `descricao_original`) ↔ `desc_id` ↔ `produto_map` "
             "do banco de trabalho da cesta (mode=ro). A inspeção conferiu unicidade, cobertura nos dois sentidos e a soma dos itens "
             "por produto (`saidas/inspecao_entradas.json`).")
    L.append(f"- Colunas ignoradas por conterem informação econômica ou de resultado: "
             f"{', '.join('`'+c+'`' for c in insp['mapeamento']['cesta_candidata']['colunas_ignoradas_por_conterem_informacao_economica'])}. "
             "`diagnostico_por_produto.csv` (contagens por modo) e a pasta do estudo econométrico não são abertos.")
    L.append(f"- Bancos de origem (cesta e `pncp.db` em D:) conferidos antes e depois de cada etapa: inalterados.\n")

    L.append("## 1–3. Candidatos, variantes e frequências (P1)\n")
    L.append(_tab(["Medida", "Valor"], [
        ["Candidatos P1 avaliados", _n(n)], ["Piloto (100 primeiros P1 por compras)", _n(rod["piloto_P1_100"]["man"]["contagens"]["produtos"]) if "piloto_P1_100" in rod else "—"],
        ["Descrições originais distintas examinadas (100%)", _n(m["contagens"]["descricoes_originais"])],
        ["Variantes normalizadas (decisão por variante)", _n(len(V))], ["Itens cobertos", _n(m["contagens"]["itens"])],
        ["Produtos com 1 / 2 / 3+ variantes", f"{_n(vpp.get(1, 0))} / {_n(vpp.get(2, 0))} / {_n(sum(v for k, v in vpp.items() if k >= 3))}"],
        ["Máximo de variantes num produto", _n(max(vpp))],
        ["Variantes com 1 item / com até 5 itens (raras, mantidas)", f"{_n(raras1)} / {_n(raras5)}"],
        ["Variantes sem descrição (equivalência só pelo código)", _n(sem_desc)],
        ["Mediana de itens por variante", _n(itens_v[len(itens_v) // 2])]]))
    L.append("\nAs variantes normalizadas juntam descrições que diferem só em maiúsculas, acentos, espaços, ':' e grafia de unidades; "
             "a correspondência com cada descrição original está em `descricoes_originais.csv`.\n")

    L.append("## 4–8. Resultado da auditoria automática (P1)\n")
    L.append(_tab(["Status automático", "Produtos", "%"], [[k, _n(v), _pct(v, n)] for k, v in sorted(st.items(), key=lambda kv: -kv[1])]))
    L.append(f"\n- **Atributos técnicos insuficientes** (status `ATRIBUTOS_INSUFICIENTES`): {_n(st.get('ATRIBUTOS_INSUFICIENTES', 0))}. "
             f"Produtos sem nenhum atributo tipado (só pares 'ATRIBUTO VALOR' do catálogo): {_n(so_decl)}.")
    L.append(f"- **Conflitos objetivos:** {_n(len(conf_obj))} em {_n(st.get('CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO', 0))} produto(s); "
             f"por atributo: {dict(tipos_obj) or 'nenhum'}.")
    for p in prods:
        if p["status_auditoria"] == "CONFLITO_OBJETIVO_EXIGE_DESMEMBRAMENTO":
            L.append(f"  - `{p['id_candidato']}` {p['produto']} — {p['descricao_representativa'][:90]}…: "
                     f"{'; '.join(x for x in p['conflitos'].split(' | ') if 'OBJETIVO' in x)}; "
                     f"desmembrável: {'sim' if p['desmembravel'] == '1' else 'não'} ({p['subprodutos'] or p['motivo_nao_desmembravel']}).")
    L.append(f"- **Divergências a examinar** (não objetivas: informação parcial, texto colado, espaço dentro de número, nome do item): "
             f"{_n(st.get('DIVERGENCIA_A_EXAMINAR', 0))} produtos; tipos mais frequentes: "
             f"{', '.join(f'{k} ({v})' for k, v in tipos_ex.most_common(8))}.")
    L.append(f"- **Desmembramento:** {_n(m['contagens']['produtos_desmembraveis'])} produto(s) com subprodutos reproduzíveis propostos "
             f"({_n(len(subs))} subprodutos). Nenhum subproduto é aprovado sem revisão própria.")
    L.append(f"- **Consulta a editais/termos de referência indicada:** {_n(n_edital)} produtos ({_pct(n_edital, n)}); motivos: "
             f"{', '.join(f'{k} ({v})' for k, v in edital.most_common())}.")
    L.append(f"- **Avaliação especializada indicada:** {_n(sum(1 for p in prods if p['requer_especialista']))} produtos; categorias: "
             f"{', '.join(f'{k} ({v})' for k, v in esp.most_common())}.\n")
    L.append(f"Regras na versão {m['versoes']['regras']} (normalização {m['versoes']['normalizacao']}, extração "
             f"{m['versoes']['extracao']}, auditoria {m['versoes']['auditoria']}). As correções feitas depois do exame dos falsos "
             "conflitos da primeira execução, cada uma com teste de regressão, estão em `metodologia_validacao.md` "
             "(Registro de alterações das regras).\n")

    L.append("\n## 9–11. Aprovação e cobertura\n")
    L.append(_tab(["Medida", "Valor"], [
        ["Produtos aprovados (VALIDADO)", _n(res.get("produtos_aprovados", 0))], ["Subprodutos aprovados", _n(res.get("subprodutos_aprovados", 0))],
        ["Rejeitados", _n(res.get("produtos_rejeitados", 0))], ["Pendentes", _n(res.get("produtos_pendentes", n))],
        ["Bloqueados (tentativa de aprovação sem requisitos)", _n(res.get("produtos_bloqueados", 0))],
        ["Variantes com decisão", f"{_n(res.get('variantes_avaliadas', 0))} de {_n(res.get('variantes_total', len(V)))}"],
        ["Revisores cadastrados", _n(res.get("revisores_cadastrados", 0))],
        ["Cobertura dos aprovados em compras", "—" if not val else _n(sum(int(next(p['compras'] for p in prods if p['id_candidato'] == r['id_candidato'])) for r in val))],
        ["`cesta_validada.csv`", "não criada (nenhum VALIDADO)" if not val else "criada"]]))
    L.append(f"\nPara referência, os {_n(n)} candidatos P1 somam {_n(comp_tot)} pares produto × compra; a cobertura dos aprovados "
             "será calculada pelo mesmo relatório quando houver aprovações.\n")

    L.append("## 12. Testes\n")
    if testes:
        L.append(f"`python scripts/executar.py testes` em {testes['executado_em']}: **{testes['testes_executados']} testes executados, "
                 f"{testes['aprovados']} aprovados, {testes['falhas']} falhas, {testes['erros']} erros** (Python {testes['python']}). "
                 "Os 25 testes obrigatórios são `test_01`…`test_25` de `testes/test_validacao.py`; os demais são regressões das "
                 "correções de regra e verificações extras (decisão inválida, não sobrescrita, mudança de entrada, mapeamento com "
                 "coluna econômica, código sem campos econômicos, rejeição documentada, especificação sem atributo essencial).\n")
    else:
        L.append("Testes ainda não executados.\n")

    L.append("## 13. Limitações do sistema automático\n")
    L.append("- A extração é por regras sobre o texto do catálogo; texto colado na fonte ('ARAMEACO', 'SOLUCAOINJETAVEL') ou números "
             "partidos por quebra de linha ('5 0') não são corrigidos: viram divergência **a examinar**, nunca equivalência automática.\n"
             "- Atributos ausentes numa variante (informação parcial) não são conflito objetivo; a revisão humana decide se a variante é equivalente.\n"
             "- 'Sem divergência detectada' só quer dizer que as descrições do catálogo coincidem; não prova que todas as compras "
             "contrataram o mesmo objeto (o edital pode exigir marca, prazo, garantia, embalagem ou entrega diferentes).\n"
             "- Variantes sem descrição (item sem `descricaodetalhada` na fonte) só podem ser ligadas pelo código CATMAT.\n"
             "- Os riscos (medicamento, peça, compatibilidade…) são sinalizações por palavras, cautelas da cesta e classe do catálogo; "
             "não substituem avaliação especializada.\n"
             "- A revisão técnica ocorre depois de resultados econométricos exploratórios já terem sido vistos; o procedimento "
             "protege a independência (formulários sem preço/modo, ordem só por compras), mas isso não torna o estudo "
             "retrospectivamente confirmatório.\n"
             "- Mesmo um produto homogêneo pode ter preços diferentes por quantidade, frete, prazo, garantia, marca, logística, "
             "qualidade contratual e mercado regional; a validação técnica melhora a comparabilidade do objeto, mas não resolve a "
             "endogeneidade da escolha do modo nem as falhas de pré-tendência do estudo econométrico.\n")
    L.append("## 14. Pendências da revisão humana\n")
    L.append(f"- Cadastrar os revisores em `config/revisores.csv` (identificação e qualificação controladas pela pesquisa).\n"
             f"- Decidir as {_n(len(V))} variantes P1 em `saidas/P1/revisao_variantes.csv` (EQUIVALENTE/DIVERGENTE/INDETERMINADA, "
             "com fundamentação, fonte, revisor e data).\n"
             f"- Decidir os {_n(n)} produtos e {_n(len(subs))} subprodutos em `saidas/P1/revisao_produtos.csv`, começando pelo piloto "
             "(`saidas/piloto_P1_100/`), com especificação canônica `NOME | ATRIBUTO: VALOR | …` que inclua os atributos essenciais "
             "(coluna `atributos_consenso`).\n"
             f"- Produto com conflito objetivo: decidir DESMEMBRAR (e então revisar os subprodutos) ou REJEITAR.\n"
             f"- Consultar editais/termos de referência nos {_n(n_edital)} produtos indicados.\n")
    L.append("## 15. Continuidade\n")
    L.append("```powershell\ncd PNCP-Automation\\analises\\validacao_tecnica_cesta_20261125\n"
             "..\\..\\.venv\\Scripts\\python.exe scripts\\executar.py concluir --rodada piloto_P1_100 --exigir-dupla-revisao\n"
             "..\\..\\.venv\\Scripts\\python.exe scripts\\executar.py concluir --exigir-dupla-revisao        # rodada P1\n"
             "..\\..\\.venv\\Scripts\\python.exe scripts\\executar.py relatorio\n```\n")
    L.append("Com aprovações, `concluir` grava `saidas/<rodada>/cesta_validada.csv` e `saidas/<rodada>/integracao_econometria/` "
             "(cópia dos arquivos congelados da cesta + `cesta_validada.csv` no formato original, só com produtos inteiros). O estudo "
             "econométrico roda de novo sem mudar código, com um `config.json` cujo `caminhos.cesta_pasta` aponte para essa pasta. "
             "Subprodutos exigem adaptar a ligação item × especificação atômica (`ligacao_itens_especificacoes.csv`); o CATMAT original "
             "não basta para presumir equivalência. Qualquer mudança de entrada, regra ou configuração exige nova preparação "
             "(nova `versao_auditoria`); aprovações de outra versão nunca são reaproveitadas.\n")
    L.append("## Hashes\n")
    linhas_h = []
    for r, d in rod.items():
        for k, h in d["man"]["hashes_base"].items():
            linhas_h.append([f"saidas/{r}/{k}", f"`{h}`"])
        for k, h in d["man"]["hashes_formularios_iniciais"].items():
            linhas_h.append([f"saidas/{r}/{k} (inicial)", f"`{h}`"])
        linhas_h.append([f"saidas/{r} — versão da auditoria", f"`{d['man']['versao_auditoria']}`"])
    for k, e in m["entradas"].items():
        linhas_h.append([f"entrada: {Path(e['caminho']).name}", f"`{e['sha256']}`"])
    L.append(_tab(["Arquivo", "SHA-256"], linhas_h))
    (pasta / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    manifesto = {
        "gerado_em": comum.agora(), "versao_codigo": comum.VERSAO, "rodadas": {
            r: {"pasta": f"saidas/{r}", "versao_auditoria": d["man"]["versao_auditoria"], "preparado_em": d["man"]["preparado_em"],
                "contagens": d["man"]["contagens"], "hashes_base": d["man"]["hashes_base"],
                "hashes_formularios_iniciais": d["man"]["hashes_formularios_iniciais"],
                "resultado": {k: v for k, v in (d["res"] or {}).items() if k in ("produtos_aprovados", "produtos_pendentes", "produtos_bloqueados",
                                                                              "subprodutos_aprovados", "variantes_avaliadas", "concluido_em", "aviso")}}
            for r, d in rod.items()},
        "entradas": m["entradas"], "bancos": m["bancos"], "hashes_config": m["hashes_config"], "hashes_codigo": m["hashes_codigo"],
        "testes": testes and {k: testes[k] for k in ("executado_em", "testes_executados", "aprovados", "falhas", "erros", "sucesso")},
        "documentos": {n: comum.sha256_arquivo(pasta / n) for n in ("protocolo_validacao.md", "metodologia_validacao.md", "README.md", "conclusao.md")
                       if (pasta / n).exists()},
        "relatorio_md": comum.sha256_arquivo(pasta / "relatorio.md"),
    }
    comum.escrever_json(pasta / "manifesto.json", manifesto)
    reg.log(f"relatorio.md e manifesto.json gravados em {pasta}")
