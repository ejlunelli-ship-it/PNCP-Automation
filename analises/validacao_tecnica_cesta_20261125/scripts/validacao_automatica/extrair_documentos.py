"""Extração de texto de documentos externos (PDF, DOCX, ZIP com PDF/DOCX) e localização do item pelo código CATMAT.

Conteúdo externo é dado NÃO confiável: só é lido como texto e processado por expressões regulares; nada é executado,
nenhum link é seguido, nenhuma instrução do documento é considerada. ZIPs são lidos em memória (sem gravar membros
em disco, sem caminhos), com limites de quantidade e tamanho. PDFs sem camada de texto não passam por OCR: ficam
registrados como 'sem texto extraível'.
"""
import io
import re
import zipfile

from .normalizar_texto import compacto, contem_tolerante, normalizar, texto_seguro

MAX_MEMBROS, MAX_MEMBRO = 30, 40 * 1024 * 1024
# valores monetários dos documentos (preço estimado etc.) são mascarados ANTES de qualquer extração ou gravação de trecho
RX_MOEDA = re.compile(r"R\s*\$\s*-?\s*\d[\d.,]*")


def mascarar_valores(t):
    return RX_MOEDA.sub("[VALOR OMITIDO]", t)


def _pdf(dados):
    import pymupdf
    paginas = []
    with pymupdf.open(stream=dados, filetype="pdf") as doc:
        for p in doc:
            paginas.append(texto_seguro(p.get_text("text")))
    return paginas


def _docx(dados):
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return [texto_seguro(re.sub(r"<[^>]+>", "", xml))]


def extrair_texto(dados):
    """(formato, [textos por página/parte], erro)."""
    try:
        if dados[:4] == b"%PDF":
            return "pdf", _pdf(dados), None
        if dados[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(dados)) as z:
                nomes = z.namelist()
                if "word/document.xml" in nomes:
                    return "docx", _docx(dados), None
                partes = []
                for info in z.infolist()[:MAX_MEMBROS]:
                    if info.is_dir() or info.file_size > MAX_MEMBRO:
                        continue
                    b = z.read(info)
                    if b[:4] == b"%PDF":
                        partes += _pdf(b)
                    elif b[:2] == b"PK":
                        try:
                            with zipfile.ZipFile(io.BytesIO(b)) as z2:
                                if "word/document.xml" in z2.namelist():
                                    partes += _docx(b)
                        except zipfile.BadZipFile:
                            pass
                return "zip", partes, None if partes else "zip sem PDF/DOCX legível"
        return "desconhecido", [], "formato não suportado"
    except Exception as e:                            # documento corrompido ou malformado
        return "erro", [], f"{type(e).__name__}: {str(e)[:200]}"


def localizar_item(paginas, catmat, canon, extrator, contexto, janela, janela_conflito):
    """Procura o CATMAT no texto e confronta a janela em volta com a especificação canônica oficial.
    Só o texto da janela é usado (o resto do documento é ignorado). Devolve a lista de âncoras avaliadas."""
    rx = re.compile(rf"(?<!\d){re.escape(str(catmat))}(?!\d)")
    out = []
    for i, pag in enumerate(paginas):
        t = mascarar_valores(normalizar(mascarar_valores(pag)))
        for m in rx.finditer(t):
            w = t[max(0, m.start() - janela):m.end() + janela]
            wc = compacto(w)
            pres, aus, tol = [], [], []
            for c in canon["caracteristicas"]:
                if not c["valor_compacto"]:
                    continue
                achou, t_ = contem_tolerante(c["valor"], wc)
                (tol if (achou and t_) else pres if achou else aus).append(c["nome"])
            estreita = t[max(0, m.start() - janela_conflito):m.end() + janela_conflito]
            tv = {a: set(d) for a, d in extrator.extrair(estreita, contexto).items()}
            confl = [f"{a}: oficial {'/'.join(o)} × documento {'/'.join(sorted(tv[a]))}"
                     for a, o in canon["atributos_tipados"].items() if a in tv and tv[a] and not (set(o) & tv[a])]
            out.append({"pagina": i + 1, "posicao": m.start(), "presentes": pres, "ausentes": aus, "tolerados": tol,
                        "possiveis_conflitos": confl, "trecho": texto_seguro(t[max(0, m.start() - 200):m.end() + 300], 600)})
    return out


def avaliar_ancoras(ancoras):
    """VALIDADO se alguma âncora traz TODOS os valores oficiais e nenhuma divergência possível na janela estreita."""
    if not ancoras:
        return "SEM_ANCORA", None
    boas = [a for a in ancoras if not a["ausentes"] and not a["possiveis_conflitos"] and (a["presentes"] or a["tolerados"])]
    if boas:
        return "COMPATIVEL", boas[0]
    if any(a["possiveis_conflitos"] for a in ancoras):
        return "POSSIVEL_DIVERGENCIA", next(a for a in ancoras if a["possiveis_conflitos"])
    return "INSUFICIENTE", max(ancoras, key=lambda a: len(a["presentes"]) + len(a["tolerados"]))
