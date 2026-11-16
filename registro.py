"""Registro compartilhado (versionado no git) do que já foi buscado e baixado.

Os PDFs ficam em dados/ (fora do git); o registro fica em registro/, na raiz do repositório:

    registro/aberto-fechado_<AAAA-MM>/<usuario>_api.csv      baixar_api.py (busca no PNCP)
    registro/aberto-fechado_<AAAA-MM>/<usuario>_manual.csv   baixar_manual.py (zip baixado à mão)

Cada pessoa só acrescenta linhas aos próprios arquivos, então o git não tem conflito de merge. O estado
é a união de todos os arquivos: depois de um `git pull`, os scripts pulam o que qualquer um já resolveu.
O usuário vem do `git config user.name` (ou da variável PNCP_USUARIO).

Para duas pessoas não pegarem a mesma compra entre um push e um pull, dividam as compras com
`--parte k/n` nos dois scripts: cada compra cai sempre na mesma parte, pelo numeroControlePNCP.

Uso: python registro.py migrar [AAAA-MM ...]   (passa os motivos.csv/manual.csv antigos de dados/ para
     registro/; sem mês, todos)
"""
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from config import DADOS

REGISTRO = Path(os.environ.get("PNCP_REGISTRO") or Path(__file__).parent / "registro")
COLUNAS = ["numeroControlePNCP", "idCompra", "usuario", "data_hora", "passada", "situacao", "motivo",
           "itens_cobertos", "itens", "sha256", "publicados", "candidatos", "outros_guardados", "erros"]
RE_ITEM = re.compile(r"-item-(\d+)\.pdf$", re.I)
GIT = ["git", r"C:\Program Files\Git\cmd\git.exe"]
_usuario = None


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
    """Acrescenta a linha de uma compra a registro/aberto-fechado_<mes>/<usuario>_<origem>.csv."""
    linha = {"usuario": usuario(), "data_hora": datetime.now().isoformat(timespec="seconds"), **linha}
    _escrever(REGISTRO / f"aberto-fechado_{mes}" / f"{usuario()}_{origem}.csv", [linha])


def _legados():
    pasta = DADOS / "filtrados"
    return sorted(pasta.glob("aberto-fechado_*/motivos.csv")) + sorted(pasta.glob("aberto-fechado_*/manual.csv"))


def ler():
    """Todas as linhas do registro (de todos os usuários) e dos arquivos antigos ainda não migrados,
    com o mês em `mes`. A ordem entre arquivos não vale: quem usa deve dar prioridade a 'completo'."""
    linhas = []
    for arquivo in sorted(REGISTRO.glob("aberto-fechado_*/*.csv")) + _legados():
        with open(arquivo, newline="", encoding="utf-8-sig") as f:
            linhas += [{**l, "mes": arquivo.parent.name.split("_")[-1]} for l in csv.DictReader(f)]
    return linhas


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
    if sys.argv[1:2] == ["migrar"]:
        migrar(sys.argv[2:])
    else:
        print(__doc__)
