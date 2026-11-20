"""Registro compartilhado (versionado no git) do que já foi buscado e baixado.

Os PDFs ficam em dados/ (fora do git); o registro fica em registro/, na raiz do repositório:

    registro/aberto-fechado_<AAAA-MM>/<usuario>_api.csv      baixar_api.py (busca no PNCP)
    registro/aberto-fechado_<AAAA-MM>/<usuario>_manual.csv   baixar_manual.py (zip baixado à mão)

Cada pessoa só acrescenta linhas aos próprios arquivos, então o git não tem conflito de merge. O estado
é a união de todos os arquivos: depois de um `git pull`, os scripts pulam o que qualquer um já resolveu.
O usuário vem do `git config user.name` (ou da variável PNCP_USUARIO).

Para duas pessoas não pegarem a mesma compra entre um push e um pull, dividam as compras com
`--parte k/n` nos dois scripts: cada compra cai sempre na mesma parte, pelo numeroControlePNCP.

A lista das compras a baixar (Aberto-Fechado com item homologado, pelo mês do resultado) também fica
aqui, em registro/compras/<AAAA-MM>.csv: quem não tem o dados/pncp.db (16 GB) usa essa lista.

Modo de disputa (--modo): o padrão é aberto-fechado. Com --modo fechado-aberto vale a mesma seleção,
para os pregões Fechado-Aberto, com pastas próprias: registro/fechado-aberto_<AAAA-MM>/,
registro/compras_fechado-aberto/<AAAA-MM>.csv e dados/filtrados/fechado-aberto_<AAAA-MM>/.

Uso: python registro.py migrar [AAAA-MM ...]   passa os motivos.csv/manual.csv antigos de dados/ para
                                               registro/ (sem mês, todos)
     python registro.py compras                regera registro/compras/ a partir do dados/pncp.db
     python registro.py compras --modo fechado-aberto   idem, em registro/compras_fechado-aberto/
"""
import csv
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from config import DADOS

REGISTRO = Path(os.environ.get("PNCP_REGISTRO") or Path(__file__).parent / "registro")
COLUNAS = ["numeroControlePNCP", "idCompra", "usuario", "data_hora", "passada", "situacao", "motivo",
           "itens_cobertos", "itens", "sha256", "publicados", "candidatos", "outros_guardados", "erros"]
# modo de disputa da amostra: prefixo das pastas -> valor de compras.modo_disputa no pncp.db
MODOS = {"aberto-fechado": "Aberto-Fechado", "fechado-aberto": "Fechado-Aberto"}
MODO = "aberto-fechado"
CAMPOS_COMPRA = ["numeroControlePNCP", "idCompra", "numeroCompra", "anoCompraPncp", "objetoCompra",
                 "dataPublicacaoPncp", "dataAberturaPropostaPncp", "orgaoEntidadeCnpj"]
TAMANHO_OBJETO = 100  # o objeto só aparece na tela; cortado, a lista fica com metade do tamanho
SELECAO = """
SELECT DISTINCT substr(i.data_resultado, 1, 7) AS mes,
       c.numero_controle_pncp AS numeroControlePNCP, c.id_compra AS idCompra,
       c.numero_compra AS numeroCompra, c.ano_compra AS anoCompraPncp, c.objeto_compra AS objetoCompra,
       c.data_publicacao AS dataPublicacaoPncp, c.data_abertura_proposta AS dataAberturaPropostaPncp,
       c.orgao_cnpj AS orgaoEntidadeCnpj
FROM compras c JOIN itens i USING (numero_controle_pncp)
WHERE i.registro_principal = 1 AND i.homologado = 1 AND c.modo_disputa = ?
  AND c.id_compra IS NOT NULL AND i.data_resultado LIKE ?
ORDER BY 2
"""
RE_ITEM = re.compile(r"-item-(\d+)\.pdf$", re.I)
GIT = ["git", r"C:\Program Files\Git\cmd\git.exe"]
_usuario = None


def usar_modo(modo):
    """Troca o modo de disputa (aberto-fechado ou fechado-aberto) usado pelas funções deste módulo."""
    global MODO
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r} (use {', '.join(MODOS)})")
    MODO = modo


def pasta_compras():
    """registro/compras/ (Aberto-Fechado, nome de sempre) ou registro/compras_<modo>/."""
    return REGISTRO / ("compras" if MODO == "aberto-fechado" else f"compras_{MODO}")


def usuario():
    """Nome do usuário em minúsculas, sem acento, com hífens: 'Eduardo José Lunelli' -> 'eduardo-jose-lunelli'."""
    global _usuario
    if _usuario:
        return _usuario
    nome = os.environ.get("PNCP_USUARIO")
    for git in ([] if nome else GIT):
        try:
            nome = subprocess.run([git, "config", "user.name"], capture_output=True, encoding="utf-8",
                                  errors="replace", cwd=Path(__file__).parent).stdout.strip()
        except OSError:
            continue
        if nome:
            break
    if not nome:
        sys.exit("Usuário desconhecido: configure `git config user.name` ou a variável PNCP_USUARIO.")
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    _usuario = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return _usuario


def parte(texto):
    """'k/n' -> (k, n), validado."""
    m = re.fullmatch(r"(\d+)/(\d+)", texto or "")
    if not m or not 1 <= int(m[1]) <= int(m[2]):
        raise ValueError("parte no formato k/n, com 1 <= k <= n (ex.: 2/3)")
    return int(m[1]), int(m[2])


def na_parte(controle, k_n):
    """A compra cai na parte k de n? Estável entre máquinas (não usa o hash() do Python)."""
    if not k_n:
        return True
    k, n = k_n
    return int(hashlib.sha1(controle.encode()).hexdigest(), 16) % n == k - 1


def termos(caminhos):
    """(itens, sha256) dos termos escolhidos: itens '1;2;5' e um hash único do conjunto de arquivos."""
    caminhos = sorted(caminhos, key=lambda c: Path(c).name)
    itens = sorted({int(m[1]) for c in caminhos if (m := RE_ITEM.search(Path(c).name))})
    h = hashlib.sha256()
    for c in caminhos:
        h.update(Path(c).name.encode() + b"\0" + hashlib.sha256(Path(c).read_bytes()).digest())
    return ";".join(map(str, itens)), (h.hexdigest() if caminhos else "")


def _escrever(arquivo, linhas):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore", lineterminator="\n")
        if novo:
            w.writeheader()
        w.writerows(linhas)


def anotar(mes, origem, linha):
    """Acrescenta a linha de uma compra a registro/<modo>_<mes>/<usuario>_<origem>.csv."""
    linha = {"usuario": usuario(), "data_hora": datetime.now().isoformat(timespec="seconds"), **linha}
    _escrever(REGISTRO / f"{MODO}_{mes}" / f"{usuario()}_{origem}.csv", [linha])


def _legados():
    pasta = DADOS / "filtrados"
    return sorted(pasta.glob(f"{MODO}_*/motivos.csv")) + sorted(pasta.glob(f"{MODO}_*/manual.csv"))


def ler():
    """Todas as linhas do registro (de todos os usuários) e dos arquivos antigos ainda não migrados,
    com o mês em `mes`. A ordem entre arquivos não vale: quem usa deve dar prioridade a 'completo'."""
    linhas = []
    for arquivo in sorted(REGISTRO.glob(f"{MODO}_*/*.csv")) + _legados():
        with open(arquivo, newline="", encoding="utf-8-sig") as f:
            linhas += [{**l, "mes": arquivo.parent.name.split("_")[-1]} for l in csv.DictReader(f)]
    return linhas


def _banco():
    banco = DADOS / "pncp.db"
    if not banco.exists():
        return None
    con = sqlite3.connect(f"file:{banco.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def compras_do_mes(mes):
    """Compras do modo com item homologado no mês: do dados/pncp.db ou, sem ele, de registro/compras[_<modo>]/."""
    con = _banco()
    if con is not None:
        linhas = [{k: r[k] for k in CAMPOS_COMPRA} for r in con.execute(SELECAO, (MODOS[MODO], f"{mes}%"))]
        con.close()
        return linhas
    arquivo = pasta_compras() / f"{mes}.csv"
    if not arquivo.exists() and arquivo.parent.is_dir():
        return []  # a lista foi exportada e o mês não tem compra do modo (ex.: Fechado-Aberto em 2023-04)
    if not arquivo.exists():
        sys.exit(f"Sem dados/pncp.db e sem {arquivo.relative_to(REGISTRO.parent)}: rode `git pull`.")
    with open(arquivo, newline="", encoding="utf-8") as f:
        return [{**l, "anoCompraPncp": int(l["anoCompraPncp"])} for l in csv.DictReader(f)]


def exportar_compras():
    """Regrava registro/compras[_<modo>]/<mês>.csv com a seleção atual do dados/pncp.db (consulta demorada)."""
    con = _banco()
    if con is None:
        sys.exit("Sem dados/pncp.db.")
    por_mes = {}
    for r in con.execute(SELECAO, (MODOS[MODO], "%")):
        if r["mes"]:
            linha = {k: r[k] for k in CAMPOS_COMPRA}
            linha["objetoCompra"] = " ".join((linha["objetoCompra"] or "").split())[:TAMANHO_OBJETO]
            por_mes.setdefault(r["mes"], []).append(linha)
    con.close()
    pasta = pasta_compras()
    pasta.mkdir(parents=True, exist_ok=True)
    for mes, linhas in sorted(por_mes.items()):
        with open(pasta / f"{mes}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_COMPRA, lineterminator="\n")
            w.writeheader()
            w.writerows(linhas)
    print(f"registro/{pasta.name}: {sum(map(len, por_mes.values()))} compra(s)-mês em {len(por_mes)} mês(es)")


def migrar(meses=()):
    """Passa os motivos.csv/manual.csv de dados/ para registro/, no nome do usuário atual, e os apaga.
    Não rode enquanto o baixar_api.py ou o baixar_manual.py antigo estiver gravando no mês."""
    for arquivo in _legados():
        mes = arquivo.parent.name.split("_")[-1]
        if meses and mes not in meses:
            continue
        origem = "api" if arquivo.name == "motivos.csv" else "manual"
        with open(arquivo, newline="", encoding="utf-8-sig") as f:
            linhas = [{**l, "usuario": usuario()} for l in csv.DictReader(f)]
        destino = REGISTRO / arquivo.parent.name / f"{usuario()}_{origem}.csv"
        _escrever(destino, linhas)
        shutil.copy2(arquivo, arquivo.with_name(arquivo.name + ".migrado"))
        arquivo.unlink()
        print(f"{arquivo.relative_to(DADOS)}: {len(linhas)} linha(s) -> {destino.relative_to(REGISTRO.parent)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argumentos = sys.argv[1:]
    if "--modo" in argumentos:
        i = argumentos.index("--modo")
        try:
            usar_modo(argumentos[i + 1] if i + 1 < len(argumentos) else "")
        except ValueError as e:
            sys.exit(str(e))
        del argumentos[i:i + 2]
    if argumentos[:1] == ["migrar"]:
        migrar(argumentos[1:])
    elif argumentos == ["compras"]:
        exportar_compras()
    else:
        print(__doc__)
