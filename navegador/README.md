# navegador/

Scripts que rodam **dentro do navegador**, não no Python.

## `compras_auto.user.js`

Userscript (Tampermonkey) usado por `python baixar_manual.py --auto`. Nas abas que o script abre (com
`&pncpauto=1` na URL), ele clica em **Downloads relacionados a compra > Todos os relatórios e termos** e
fecha a aba quando o zip chega. Quando a compra não tem zip, baixa um aviso
`pncp-auto-<idCompra>-<motivo>.txt` com um diagnóstico da página. O `baixar_manual.py` lê esse aviso e o
guarda em `dados/avisos_auto/`.

O hCaptcha **não é contornado**: o próprio site gera o token, como num clique feito à mão. Se aparecer um
desafio, a aba espera você resolver (título `[PNCP auto] resolva o captcha`).

### Instalação (uma vez por navegador)

1. Instale a extensão **Tampermonkey** no navegador padrão do sistema, que é o que o Python abre.
   No Chrome, ative também "Permitir scripts de usuário" nos detalhes da extensão.
2. Tampermonkey > Criar um novo script: apague o modelo, cole todo o conteúdo de `compras_auto.user.js`
   e salve (Ctrl+S).
3. Desligue a pergunta de onde salvar cada arquivo (Firefox: Configurações > Geral > Arquivos e
   aplicativos; Chrome: Configurações > Downloads).

**Quando o arquivo mudar** (veja `@version` no cabeçalho), cole de novo no Tampermonkey, porque ele
guarda a própria cópia.

### Uso

```
.\.venv\Scripts\python.exe baixar_manual.py --auto                 # 20 a 60 s entre compras
.\.venv\Scripts\python.exe baixar_manual.py --auto --intervalo 0   # próxima compra assim que o zip chega
```

Detalhes, motivos registrados e resultados do teste: [docs/07 §5.3](../docs/07-metodologia-de-extracao.md).
