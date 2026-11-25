"""Relatório (relatorio.md) e registro de execução (registro_execucao.json), gerados das saídas."""
import csv
import json
import time
from pathlib import Path

from . import VERSAO, comum
from .classificacao import VERSAO_REGRAS


def _csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _fmt(x, d=0):
    if x in (None, ""):
        return "—"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x, d=1):
    return "—" if x in (None, "") else _fmt(float(x) * 100, d) + "%"


def _tabela(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in l) + " |" for l in linhas]
    return "\n".join(out)


def _hashes_codigo(pasta):
    arqs = sorted([*pasta.glob("cesta/*.py"), *pasta.glob("config/*"), pasta / "executar.py", pasta / "validar_revisao.py",
                   *pasta.glob("testes/*.py")])
    return {str(a.relative_to(pasta)).replace("\\", "/"): comum.sha256_arquivo(a) for a in arqs if a.is_file()}


def _registros_anteriores(saidas):
    regs = {}
    for p in sorted((saidas / "registros").glob("execucao_*.json")):
        regs[p.stem] = _j(p)
    return regs


def _executar(ctx, dst):
    par, saidas, reg = ctx["par"], ctx["saidas"], ctx["reg"]
    pasta = saidas.parent if (saidas.parent / "cesta").exists() else Path(__file__).resolve().parents[1]
    q = lambda s: dst.execute(s).fetchall()
    meta = {k: json.loads(v) for k, v in q("SELECT chave, valor FROM meta")}
    snap = meta.get("snapshot", {})
    regs = _registros_anteriores(saidas)
    cont = {}
    for r in regs.values():
        cont.update(r.get("contagens", {}))
    cont.update(reg.contagens)
    # contagens recalculadas das tabelas (não dependem de a execução da seleção ter gravado o registro)
    um = lambda sql: dst.execute(sql).fetchone()[0]
    cont["familias_universo"] = um("SELECT COUNT(*) FROM fam_metricas")
    cont["familias_triagem_ampla"] = um("SELECT COUNT(*) FROM familia_classe")
    cont["familias_passam_limiares_iniciais"] = um("SELECT SUM(passa_inicial) FROM familia_classe")
    cont["familias_iniciais_falham_qualidade_cadastral"] = um(
        "SELECT SUM(passa_inicial AND NOT cadastral_ok) FROM familia_classe")
    cont["produtos_candidatos"] = um("SELECT COUNT(*) FROM cesta_candidata_tab")
    if (saidas / "sensibilidade_grade.csv").exists():
        cont["sensibilidade_cenarios_grade"] = len(_csv(saidas / "sensibilidade_grade.csv"))
    # ruptura da fonte: itens de material de pregão eletrônico sem código de catálogo, por mês
    ruptura = dst.execute(
        "SELECT substr(c.data_publicacao, 1, 7) AS mes, COUNT(*) AS itens_material, SUM(i.catmat IS NULL) AS sem_catmat "
        "FROM itens i JOIN compras_base c USING (chave) WHERE c.modalidade = ? AND i.material_ou_servico = 'M' "
        "AND c.data_publicacao IS NOT NULL GROUP BY 1 ORDER BY 1", (par["universo"]["modalidade"],)).fetchall()
    ultima_catmat = um("SELECT MAX(data_publicacao) FROM universo")
    temporal = _j(saidas / "cobertura_temporal.json")
    funil = _csv(saidas / "funil_selecao.csv")
    cesta = _csv(saidas / "cesta_candidata.csv")
    aud = _j(saidas / "auditoria_qualidade.json")
    cob = _j(saidas / "cobertura_cesta.json")
    cong = _j(saidas / "congelamento_cesta.json")
    cen = _csv(saidas / "sensibilidade_cenarios.csv") if (saidas / "sensibilidade_cenarios.csv").exists() else []
    inter = _csv(saidas / "sensibilidade_intersecoes.csv") if (saidas / "sensibilidade_intersecoes.csv").exists() else []
    uma = _csv(saidas / "sensibilidade_uma_dimensao.csv") if (saidas / "sensibilidade_uma_dimensao.csv").exists() else []
    diag = _j(saidas / "diagnostico_viabilidade.json") if (saidas / "diagnostico_viabilidade.json").exists() else None
    rec = _csv(saidas / "recorrencia_temporal.csv") if (saidas / "recorrencia_temporal.csv").exists() else []
    if rec:
        cont["recorrencia"] = {"produtos": len(rec), "comum_primeira_janela": sum(int(r["comum_primeira_janela"]) for r in rec),
                               "presente_todas_janelas": sum(int(r["presente_todas_janelas"]) for r in rec),
                               "criterio_comum_primeira_janela": par["temporal"].get("recorrencia_pre", {"compras_min": 10, "uasgs_min": 5})}
    descart = _csv(saidas / "familias_triadas_descartadas.csv")
    fam_classe = q("SELECT classe_tecnica, passa_inicial, cadastral_ok, COUNT(*) FROM familia_classe GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")
    univ_c = q("SELECT fonte, modalidade, situacao, compras, data_min, data_max FROM universo_compras")
    univ_i = q("SELECT fonte, modalidade, material_ou_servico, tem_catalogo, linhas, itens FROM universo_itens")
    lim = par["triagem_inicial"]
    n_var = len(_csv(saidas / "descricoes_variantes.csv")) if (saidas / "descricoes_variantes.csv").exists() else 0

    L = []
    A = L.append
    A("# Cesta padronizada de produtos (CATMAT × unidade) — PNCP")
    A("")
    A(f"Gerado em {time.strftime('%d/%m/%Y %H:%M')} pelo `executar.py` (código {VERSAO}, regras de classificação "
      f"{VERSAO_REGRAS}). Protocolo: [`protocolo.md`](protocolo.md). Todos os números vêm de `saidas/`.")
    A("")
    A("> **Escopo.** Construção e auditoria da cesta, sem estimar efeito de modo de disputa. Nenhuma etapa de seleção "
      "lê preço, desconto, valor estimado/homologado ou o modo de disputa: essas colunas nem são copiadas para o banco "
      "de trabalho (verificado por teste estático e por teste metamórfico: trocar preços e modos não muda a cesta).")
    A("")
    A("## 1. Resultado em uma tabela")
    A("")
    ncls = {k: sum(1 for c in cesta if c["classe_tecnica"] == k) for k in "AB"}
    A(_tabela(["Medida", "Valor"], [
        ["Período coberto (data de publicação)", f"{temporal['data_minima']} a {temporal['data_maxima']}"],
        ["Universo: itens de material com CATMAT em pregão eletrônico", _fmt(funil[-1]["itens"])],
        ["Universo: compras distintas / UASGs", f"{_fmt(funil[-1]['compras'])} / {_fmt(funil[-1]['uasgs'])}"],
        ["Famílias CATMAT × unidade no universo", _fmt(cont.get("familias_universo"))],
        ["Famílias que passam os limiares iniciais", _fmt(cont.get("familias_passam_limiares_iniciais"))],
        ["Produtos na cesta candidata (A + B)", f"{len(cesta)} (A = {ncls['A']}, B = {ncls['B']})"],
        ["Compras cobertas pela cesta", f"{_fmt(cob['compras'])} ({_fmt(cob['pct_compras_universo_catmat'], 1)}% do universo; "
                                        f"{_fmt(cob['pct_compras_pregao_eletronico'], 1)}% dos pregões eletrônicos da fonte)"],
        ["UASGs / CNPJs compradores na cesta", f"{_fmt(cob['uasgs'])} / {_fmt(cob['orgaos_cnpj'])}"],
        ["Cesta validada", cong["situacao_cesta_validada"]],
    ]))
    A("")
    A("A **cesta validada está vazia de propósito**: só um revisor humano pode aprovar produtos, preenchendo "
      "`saidas/formulario_revisao.csv` e rodando `validar_revisao.py`. A classe A indica apenas maior viabilidade de "
      "auditoria, não aprovação.")
    A("")
    A("## 2. Base de dados e reprodutibilidade")
    A("")
    an = snap.get("antes", {})
    A(_tabela(["Item", "Valor"], [
        ["Banco", f"`{an.get('caminho')}`"], ["Tamanho", f"{_fmt(an.get('tamanho_bytes'))} bytes"],
        ["Modificado em", an.get("mtime_iso")], ["Contador de alterações SQLite", an.get("sqlite_contador_alteracoes")],
        ["SHA-256 (64 MB iniciais + 64 MB finais)", f"`{an.get('sha256_inicio_fim')}`"],
        ["Banco inalterado ao fim da leitura", "sim (impressão digital idêntica)" if snap.get("depois") == an or
         (snap.get("depois") or {}).get("sha256_inicio_fim") == an.get("sha256_inicio_fim") else "NÃO CONFERIDO"],
        ["Modo de abertura", "`mode=ro` + `PRAGMA query_only`, uma transação de leitura (snapshot) por etapa"],
        ["Python / SQLite", f"{comum.ambiente()['python'].split()[0]} / {comum.ambiente()['sqlite']}"],
        ["Banco de trabalho", f"`{ctx['trabalho_db']}` (fora do git; índices e tabelas intermediárias só nele)"],
        ["Banco lido no diagnóstico", f"`{ctx['cam']['db']}`" + (" — o arquivo foi movido durante o estudo; tamanho, mtime, "
         "contador de alterações e SHA-256 iguais aos da extração (conferido pelo diagnóstico)"
         if str(ctx['cam']['db']) != an.get('caminho') else "")],
    ]))
    A("")
    A("Hashes de todos os arquivos de código e configuração: `registro_execucao.json`.")
    A("")
    A("## 3. Esquema real e decisões de mapeamento")
    A("")
    A("O mapeamento campo lógico → coluna está em `saidas/esquema/mapeamento_colunas.json`; a inspeção completa "
      "(tabelas, colunas, índices, chaves, amostras) em `saidas/esquema/esquema_inspecionado.json`. Decisões:")
    A("")
    A("- **Compra** = `compras.numero_controle_pncp` (chave primária). `id_compra` não é único e **não** é usado para agrupar.")
    A("- **Item** = chave composta (`numero_controle_pncp`, `numero_item`). Os registros repetidos do mesmo item são colapsados; "
      "`registro_principal` não é usado, porque prioriza o valor do resultado (critério monetário).")
    A("- **UASG** = `compras.uasg` (unidade que realizou o pregão); `itens.uasg_item` é auditada contra ela. **CNPJ** "
      "(`orgao_cnpj`) é preservado, mas não define diversidade: várias UASGs compartilham CNPJ.")
    A("- **CATMAT** = `itens.cod_item_catalogo` com `material_ou_servico = 'M'`; códigos com `S` (CATSER) ficam fora.")
    A("- **Descrição**: no `pncp.db`, `descricao_resumida` da fonte `dados_abertos` é só o nome do item no catálogo (nível PDM). "
      "A descrição completa (`descricaodetalhada`) e o nome do PDM vêm dos CSVs brutos que originaram a carga "
      f"(`dados/brutos/<ano>/itens_pregao_*.csv`, só leitura, SHA-256 por arquivo no banco de trabalho). A ligação é pela "
      f"chave composta, com conferência de cardinalidade: {_fmt(cont.get('brutos_linhas'))} linhas nos brutos e no banco, "
      f"divergências: {cont.get('ligacao_divergencias') or 'nenhuma'}.")
    A("- **Data de referência** = `data_publicacao` (sempre presente); `data_abertura_proposta` só é auditada.")
    A("- **Fonte**: só `fonte = 'dados_abertos'` (Compras.gov.br) tem CATMAT e UASG. As compras `fonte = 'pncp'` "
      "(outras plataformas) entram só na contagem descritiva abaixo.")
    A("")
    A("### Universo total do PNCP no banco (descritivo, não altera a cesta)")
    A("")
    A(_tabela(["Fonte", "Modalidade", "Situação", "Compras", "Publicação mín.", "Publicação máx."],
              [[a, b, c or "—", _fmt(d), (e or "")[:10], (f or "")[:10]] for a, b, c, d, e, f in univ_c]))
    A("")
    A(_tabela(["Fonte", "Modalidade", "M/S", "Com código de catálogo", "Linhas", "Itens"],
              [[a, b, c, "sim" if d else "não", _fmt(e), _fmt(f)] for a, b, c, d, e, f in univ_i]))
    A("")
    A("## 4. Cobertura temporal")
    A("")
    A(f"Toda a cobertura disponível foi usada, inclusive 2026, sem corte em 2025: publicações de **{temporal['data_minima']}** "
      f"a **{temporal['data_maxima']}** ({temporal['trimestres']} trimestres, {temporal['anos']} anos).")
    A("")
    A("- Trimestres parcialmente observados: " + ", ".join(f"{t} ({len(m)} meses: {', '.join(m)})" for t, m in temporal["trimestres_parciais"].items()) + ".")
    A("- Anos parcialmente observados: " + ", ".join(f"{a} ({n} meses)" for a, n in temporal["anos_parciais"].items()) + ".")
    A("- Os meses mais recentes têm menos itens homologados (resultados ainda em andamento na data da carga).")
    A("")
    A("### Ruptura da fonte em abril de 2026")
    A("")
    A(f"O último item com CATMAT foi publicado em **{ultima_catmat}**. A partir de meados de abril de 2026 a API Dados "
      "Abertos passou a entregar os itens **sem** `codItemCatalogo`, `codigoPdm`, `codigoClasse`, `nomePdm` e "
      "`descricaodetalhada` (conferido no banco, nos CSVs e nos JSONs brutos; o esquema dos arquivos não mudou e a "
      "`descricaoResumida` passou a trazer texto livre do órgão). Esses meses existem no banco, mas os itens não são "
      "identificáveis por CATMAT e ficam fora do universo pela etapa 3 do funil. A cobertura utilizável da cesta é, "
      "portanto, de 2022-11 a 2026-04; 2026 aparece só com 3,5 meses.")
    A("")
    A(_tabela(["Mês", "Itens de material", "Sem CATMAT", "% sem CATMAT"],
              [[m, _fmt(n), _fmt(z), _fmt(100 * z / n, 1)] for m, n, z in ruptura if m >= "2025-10"]))
    A("")
    sem_antes = sum(z for m, n, z in ruptura if m < "2026-04")
    tot_antes = sum(n for m, n, z in ruptura if m < "2026-04")
    A(f"Antes de 2026-04, {_fmt(sem_antes)} de {_fmt(tot_antes)} itens de material ({_fmt(100 * sem_antes / tot_antes, 1)}%) não têm "
      "CATMAT (itens não catalogados); o restante da perda da etapa 3 vem da ruptura.")
    A("")
    A("## 5. Funil de seleção")
    A("")
    A(_tabela(["Etapa", "Critério", "Itens", "Compras", "UASGs", "Itens perdidos", "% perdido"],
              [[f["etapa"], f["criterio"], _fmt(f["itens"]), _fmt(f["compras"]), _fmt(f["uasgs"]),
                _fmt(f.get("itens_perdidos")), _fmt(f.get("pct_itens_perdidos_etapa"), 2)] for f in funil]))
    A("")
    A(f"Depois do funil: {_fmt(cont.get('familias_universo'))} famílias; {_fmt(cont.get('familias_triagem_ampla'))} na triagem "
      f"ampla (cenário mais brando da grade, classificadas por completo); {_fmt(cont.get('familias_passam_limiares_iniciais'))} "
      f"passam os limiares iniciais; {_fmt(cont.get('familias_iniciais_falham_qualidade_cadastral'))} destas falham a qualidade "
      f"cadastral; {_fmt(cont.get('produtos_candidatos'))} produtos candidatos.")
    A("")
    A("## 6. Critérios de triagem (registrados antes da seleção)")
    A("")
    A(_tabela(["Critério", "Valor inicial"], [["Compras distintas", f"≥ {lim['compras_min']}"], ["UASGs distintas", f"≥ {lim['uasgs_min']}"],
                                             ["Trimestres com compras", f"≥ {lim['trimestres_min']}"], ["Anos com compras", f"≥ {lim['anos_min']}"],
                                             ["Participação da UASG dominante", f"≤ {_pct(lim['share_uasg_dominante_max'], 0)}"],
                                             ["HHI institucional", f"≤ {_fmt(lim['hhi_max'], 2)}"],
                                             ["Descrição completa (qualidade cadastral)", f"≥ {_pct(par['qualidade_cadastral']['share_descricao_completa_min'], 0)} dos itens"]]))
    A("")
    A("São parâmetros de triagem, não limiares validados. A frequência é contada em **compras distintas**: várias linhas do "
      "mesmo produto na mesma compra contam uma compra (o número de itens é guardado à parte). HHI = soma dos quadrados das "
      "participações das UASGs nas compras da família; número efetivo de UASGs = 1/HHI.")
    A("")
    A("## 7. Auditoria de homogeneidade das descrições")
    A("")
    A(f"Todas as variantes de descrição das famílias da triagem ampla foram examinadas: **{_fmt(n_var)} variantes** em "
      "`saidas/descricoes_variantes.csv` (100%: descrição original e normalizada, frequência, UASGs, período, frequência "
      "acumulada, expressões numéricas, unidades físicas, embalagem, indicadores, campos ausentes). Atributos extraídos por "
      "expressões regulares (`cesta/atributos.py`); nenhum modelo de linguagem ou classificador probabilístico foi usado.")
    A("")
    A("Constatação central: a `descricaodetalhada` da API é, na quase totalidade, o **texto do próprio item do catálogo "
      "CATMAT** (PDM + atributos), com variações de formatação (`MATERIAL: METAL ,` × `MATERIAL METAL,`). Portanto a "
      "auditoria mede a especificidade e a estabilidade da descrição de catálogo, não as exigências adicionais que cada "
      "termo de referência possa ter feito — que não estão na base. Isso limita o significado da classe A.")
    A("")
    A(_tabela(["Classe", "Passa limiares iniciais", "Qualidade cadastral OK", "Famílias"],
              [[c, "sim" if p else "não", "sim" if k else "não", _fmt(n)] for c, p, k, n in fam_classe]))
    A("")
    A("Regras (determinísticas, `cesta/classificacao.py`, parâmetros em `parametros.json → homogeneidade`):")
    A("")
    A("- **C (inadequado)**: descrição completa em < 50% dos itens; unidade ausente/irreconhecível; descrição dominante sem "
      "atributos além do nome do PDM; descrição genérica na maioria; nenhuma assinatura de atributos majoritária; peça cuja "
      "referência/aplicação define o objeto.")
    A(f"- **A (alta padronização observável)**: descrição dominante (por chave textual) em ≥ {_pct(par['homogeneidade']['share_descricao_dominante_min_A'], 0)} "
      f"dos itens; uma única assinatura de atributos; ≥ {par['homogeneidade']['min_atributos_especificos_A']} atributos declarados; "
      "descrição completa ≥ 95%; sem indício de embalagem distinta, marca/modelo, compatibilidade ou aplicação; unidade sem alerta.")
    A("- **B (revisão especializada)**: os demais. Subtipos separados automaticamente por assinatura de atributos (só quando "
      "todas as variantes têm assinatura inequívoca com o mesmo conjunto de atributos) ficam no máximo em B.")
    A("- Categorias de cautela (`config/cautela.json`: medicamentos, combustíveis, toners, eletrônicos, informática, peças, "
      "químicos, perecíveis, logística, certificação) **não excluem**: geram alerta e pendência de revisão especializada.")
    A("")
    A("## 8. Cesta candidata")
    A("")
    A(f"`saidas/cesta_candidata.csv`: {len(cesta)} produtos (congelada em {cong['congelado_em']}, SHA-256 "
      f"`{cong['sha256_cesta_candidata'][:16]}…`). Os 40 com mais compras:")
    A("")
    top = sorted(cesta, key=lambda c: -int(c["compras"]))[:40]
    A(_tabela(["ID", "CATMAT", "Unidade", "Descrição representativa", "Compras", "UASGs", "Trim.", "HHI", "Classe"],
              [[c["id_candidato"], c["catmat"], c["unidade_norm"], (c["descricao_representativa"] or "")[:90],
                _fmt(c["compras"]), _fmt(c["uasgs"]), c["trimestres"], _fmt(c["hhi"], 4), c["classe_tecnica"]] for c in top]))
    A("")
    from collections import Counter
    alertas = Counter()
    for c in cesta:
        for a in (c["alertas_especificacao"] or "").split(" | "):
            if a:
                alertas[a.split(" (")[0].split(" em ")[0]] += 1
    A("Alertas mais frequentes na cesta candidata:")
    A("")
    A(_tabela(["Alerta", "Produtos"], [[a, n] for a, n in alertas.most_common(15)]))
    A("")
    motivos = Counter((d["motivo_descarte"] or "").split(":")[0].split(";")[0][:70] for d in descart)
    A(f"Famílias que passaram os limiares iniciais mas ficaram fora (`familias_triadas_descartadas.csv`, {len(descart)}): "
      "principais motivos — " + "; ".join(f"{m} ({n})" for m, n in motivos.most_common(8)) + ".")
    A("")
    A("**Tamanho da cesta.** Os limiares iniciais deixam passar muitos produtos porque cada CATMAT do Compras.gov.br já "
      "é um item de catálogo específico (PDM + atributos) e o universo tem 174 mil compras. A revisão humana de "
      f"{len(cesta)} produtos é inviável em bloco. Uma priorização da revisão (por exemplo, começar pela classe A do "
      "cenário rigoroso, ou por grupos de material) é uma decisão de desenho que deve ser tomada e registrada antes de "
      "qualquer análise de preços; ela não foi aplicada aqui, e os limiares não foram alterados depois de ver a cesta.")
    A("")
    A("## 9. Controle de qualidade e integridade")
    A("")
    A(_tabela(["Verificação", "Afetados", "Base", "%", "Excluídos", "Produtos candidatos afetados", "Critério"],
              [[a["verificacao"], _fmt(a["afetados"]), f"{_fmt(a['base'])} {a['base_nome']}", _fmt(a["pct"], 3),
                _fmt(a["excluidos"]), _fmt(a["impacto_produtos_candidatos"]), a["criterio"]] for a in aud]))
    A("")
    A("Exemplos auditáveis de cada verificação: `saidas/auditoria_qualidade.json`. Inconsistências estruturais (chave de "
      "compra duplicada, item sem compra no universo, cardinalidade ou CATMAT divergente entre banco e brutos) interrompem a "
      "execução com `ErroEstrutural`; nenhuma ocorreu.")
    A("")
    A("## 10. Cobertura da cesta candidata")
    A("")
    A(_tabela(["Medida", "Valor"], [
        ["Produtos", cob["produtos"]], ["Compras", _fmt(cob["compras"])], ["Itens", _fmt(cob["itens"])],
        ["% das compras do universo CATMAT", _fmt(cob["pct_compras_universo_catmat"], 2)],
        ["% dos pregões eletrônicos da fonte", _fmt(cob["pct_compras_pregao_eletronico"], 2)],
        ["% dos itens do universo", _fmt(cob["pct_itens_universo_catmat"], 2)],
        ["UASGs / CNPJs", f"{_fmt(cob['uasgs'])} / {_fmt(cob['orgaos_cnpj'])}"],
        ["HHI das compras da cesta entre UASGs (nº efetivo)", f"{_fmt(cob['hhi_compras_por_uasg_cesta'], 5)} ({_fmt(cob['n_efetivo_uasgs_cesta'], 0)})"],
        ["Produtos por UASG (mediana; p90; máx.)", f"{cob['produtos_por_uasg'].get('mediana')}; {cob['produtos_por_uasg'].get('p90')}; {cob['produtos_por_uasg'].get('max')}"],
        ["UASGs por produto (mín.; mediana; máx.)", f"{cob['uasgs_por_produto'].get('min')}; {cob['uasgs_por_produto'].get('mediana')}; {cob['uasgs_por_produto'].get('max')}"],
        ["Trimestres por produto (mín.; mediana; máx.)", f"{cob['trimestres_por_produto'].get('min')}; {cob['trimestres_por_produto'].get('mediana')}; {cob['trimestres_por_produto'].get('max')}"],
    ]))
    A("")
    A(_tabela(["Ano", "Compras", "Itens", "UASGs", "Produtos"], [[r["ano"], _fmt(r["compras"]), _fmt(r["itens"]), _fmt(r["uasgs"]), r["produtos"]] for r in cob["por_ano"]]))
    A("")
    A("Por trimestre e por grupo do catálogo: `cobertura_por_trimestre.csv`, `cobertura_por_grupo_material.csv`.")
    A("")
    A("## 11. Sensibilidade da seleção")
    A("")
    A(f"Grade fatorial pré-especificada ({_fmt(cont.get('sensibilidade_cenarios_grade'))} combinações) em `sensibilidade_grade.csv`; "
      "nível da família (sem a divisão em subtipos), classe técnica da triagem ampla. Nenhum cenário foi escolhido por "
      "maximizar observações; o inicial foi fixado antes.")
    A("")
    if cen:
        A(_tabela(["Cenário", "Base", "Compras≥", "UASGs≥", "Trim.≥", "Anos≥", "Dom.≤", "HHI≤", "Produtos", "Compras", "UASGs", "Nº efetivo", "Trim. médios"],
                  [[c["cenario"], c["base"], c["compras_min"], c["uasgs_min"], c["trimestres_min"], c["anos_min"], c["share_uasg_dominante_max"],
                    c["hhi_max"], c["produtos_familia"], _fmt(c["compras"]), _fmt(c["uasgs"]), c["n_efetivo_uasgs"], c["trimestres_medios"]] for c in cen]))
        A("")
    if inter:
        A(_tabela(["A", "B", "Produtos A", "Produtos B", "Comuns", "Só A", "Só B", "Jaccard"],
                  [[i["cenario_a"], i["cenario_b"], i["produtos_a"], i["produtos_b"], i["comuns"], i["exclusivos_a"], i["exclusivos_b"], i["jaccard"]] for i in inter]))
        A("")
    if uma:
        A("Variação de uma dimensão por vez em torno do cenário inicial:")
        A("")
        A(_tabela(["Dimensão alterada", "Compras≥", "UASGs≥", "Trim.≥", "Anos≥", "Dom.≤", "HHI≤", "Produtos", "Compras", "UASGs"],
                  [[u["dimensoes_alteradas"], u["compras_min"], u["uasgs_min"], u["trimestres_min"], u["anos_min"], u["share_uasg_dominante_max"],
                    u["hhi_max"], u["produtos_candidatos_familia"], _fmt(u["compras_cobertas"]), _fmt(u["uasgs_cobertas"])] for u in uma]))
        A("")
    A("## 12. Seleção temporal e risco de viés")
    A("")
    rc = cont.get("recorrencia", {})
    A("A cesta descritiva usa toda a cobertura. Selecionar pela frequência de todo o período pode condicionar a cesta a "
      "compras posteriores a mudanças de modo; para uma análise causal futura, a cesta deve ser re-formada num período de "
      "formação definido **antes** de olhar resultados (`sensibilidade.cesta_periodo_formacao`, parâmetro "
      "`temporal.periodo_formacao`, hoje `null` e não aplicado).")
    A("")
    if rec:
        A(f"Recorrência (`recorrencia_temporal.csv`): dos {rc.get('produtos')} produtos, {rc.get('comum_primeira_janela')} já eram "
          f"comuns na primeira janela ({par['temporal']['janelas_recorrencia'][0][0]} a {par['temporal']['janelas_recorrencia'][0][1]}; "
          f"critério {rc.get('criterio_comum_primeira_janela')}) e {rc.get('presente_todas_janelas')} aparecem em todas as janelas.")
        A("")
    A("## 13. Diagnóstico posterior de viabilidade causal (não seletivo)")
    A("")
    if diag:
        A("Executado depois do congelamento (hash da cesta conferido antes e depois). Lê o modo de disputa só aqui; nenhum "
          "produto foi removido ou incluído por causa dele.")
        A("")
        cm = diag["compras_por_modo"]
        A(_tabela(["Indicador", "Valor"], [
            ["Compras da cesta: Aberto / Aberto-Fechado / Fechado-Aberto / outro", f"{_fmt(cm.get('A'))} / {_fmt(cm.get('AF'))} / {_fmt(cm.get('FA'))} / {_fmt(cm.get('outro/ausente'))}"],
            ["UASGs que usaram A e AF (compras da cesta)", f"{_fmt(diag['uasgs_usaram_A_e_AF'])} de {_fmt(diag['uasgs_cesta'])}"],
            ["Produtos comprados nos dois modos (≥ 5 compras em cada)", f"{diag['produtos_comprados_nos_dois_modos']} ({diag['produtos_com_5_ou_mais_compras_em_cada_modo']})"],
            ["Células produto × trimestre com A e AF (com ≥ 2 UASGs)", f"{_fmt(diag['celulas_com_A_e_AF'])} de {_fmt(diag['celulas_produto_trimestre'])} ({_fmt(diag['celulas_com_A_e_AF_e_2_ou_mais_uasgs'])})"],
            ["Trocas de modo dentro da UASG (UASGs com alguma troca)", f"{_fmt(diag['trocas_de_modo_dentro_da_uasg'])} ({_fmt(diag['uasgs_com_alguma_troca'])})"],
            ["Eventos potenciais (" + diag["eventos_potenciais"]["definicao"] + ")", f"{diag['eventos_potenciais']['uasgs']} UASGs; por ano: {diag['eventos_potenciais']['por_ano_da_primeira_AF']}"],
            ["Referência interna (" + diag["referencia_interna"]["definicao"] + ")", f"{_fmt(diag['referencia_interna']['pct'], 1)}% dos itens"],
            ["Referência externa de preços", diag["referencia_externa"]],
        ]))
        A("")
    A("## 14. Limitações")
    A("")
    A("- Só o Compras.gov.br (fonte `dados_abertos`) entra: as demais plataformas não informam CATMAT no PNCP.")
    A(f"- Ruptura da fonte: depois de {ultima_catmat} a API deixou de informar CATMAT; os meses de 2026-05 a 2026-10 não "
      "entram. Recuperá-los exige nova coleta de uma fonte que traga o código do catálogo.")
    A(f"- {_fmt(next(f for f in funil if f['etapa'] == '3_catmat_valido')['itens_perdidos'])} itens de material sem código de catálogo ficam fora.")
    A("- A descrição disponível é a do catálogo; especificações adicionais dos termos de referência não estão na base. "
      "Equivalência material só pode ser confirmada na revisão humana.")
    A("- `UNIDADE 0` e `QUILOGRAMA 0` (provável codificação antiga) não foram fundidas com `UNIDADE`/`QUILOGRAMA`: famílias separadas.")
    A("- Frequência medida em itens **licitados** (qualquer situação); a frequência de **homologados** é reportada ao lado e "
      "como cenário de sensibilidade.")
    A("- Os limiares são de triagem; a sensibilidade mostra quanto a cesta depende deles.")
    A("")
    A("## 15. Reprodução")
    A("")
    A("```powershell")
    A("cd PNCP-Automation\\analises\\cesta_padronizada_20261124")
    A("..\\..\\.venv\\Scripts\\python.exe executar.py            # tudo (~1 h; lê o pncp.db só em mode=ro)")
    A("..\\..\\.venv\\Scripts\\python.exe -m unittest discover -s testes -v")
    A("..\\..\\.venv\\Scripts\\python.exe validar_revisao.py     # depois de preencher o formulário")
    A("```")
    A("")
    (pasta / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8") if pasta == saidas.parent else \
        (saidas / "relatorio.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    registro = {"versao_codigo": VERSAO, "versao_regras": VERSAO_REGRAS, "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "ambiente": comum.ambiente(), "snapshot": snap, "caminhos": {k: str(v) for k, v in ctx["cam"].items()},
                "parametros": par, "sha256_parametros": comum.sha256_arquivo(ctx["parametros_arquivo"]),
                "hashes_codigo_config": _hashes_codigo(pasta), "mapeamento": meta.get("mapeamento"),
                "brutos_arquivos": [dict(zip(["arquivo", "tamanho", "sha256", "linhas", "colunas_ausentes"], r))
                                    for r in q("SELECT * FROM brutos_arquivos ORDER BY arquivo")],
                "contagens": cont, "execucoes": {k: {"etapas": v.get("etapas"), "segundos_total": v.get("segundos_total"),
                                                     "consultas": v.get("consultas"), "avisos": v.get("avisos")}
                                                 for k, v in regs.items()},
                "saidas_sha256": {p.name: comum.sha256_arquivo(p) for p in sorted(saidas.glob("*.*")) if p.is_file()}}
    comum.escrever_json(saidas / "registro_execucao.json", registro)
    dst.close()


def executar(ctx):
    dst = comum.conectar_trabalho(ctx["trabalho_db"])
    try:
        _executar(ctx, dst)
    finally:
        try:
            dst.close()
        except Exception:
            pass
