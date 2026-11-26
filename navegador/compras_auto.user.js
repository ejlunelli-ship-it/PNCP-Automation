// ==UserScript==
// @name         PNCP-Automation: Todos os relatórios e termos
// @namespace    pncp-automation
// @version      1.4
// @description  Clica em Downloads > "Todos os relatórios e termos" nas compras abertas por `baixar_manual.py --auto`.
// @match        https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/*
// @run-at       document-start
// @grant        window.close
// ==/UserScript==
//
// Só age na aba aberta com `&pncpauto=1` na URL (o baixar_manual.py --auto acrescenta). Em qualquer
// outra visita ao site não faz nada.
//
// Não mexe no hCaptcha: o próprio site gera o token, como num clique feito à mão. Se o hCaptcha mostrar
// um desafio, a aba fica esperando você resolver (o título da aba avisa).
//
// Resultado, lido pelo baixar_manual.py na pasta Downloads:
// - zip baixado: o próprio site baixa relatorios-compra-<idCompra>.zip; a aba fecha sozinha;
// - sem zip: baixa um aviso pncp-auto-<idCompra>-<motivo>.txt e fecha a aba. Motivos: sem-opcao
//   (o menu não tem "Todos os relatórios e termos"), sem-botao (a página não mostra o botão de
//   downloads), acesso-nao-autorizado, compra-nao-encontrada, erro-download (o site avisou que não
//   conseguiu baixar), compra-anulada / compra-revogada / compra-cancelada / sem-propostas ("não houve
//   registro de proposta") (1.4: a página mostra a situação e não tem o botão; avisa em SITUACAO ms,
//   sem esperar SEM_BOTAO).
(function () {
  'use strict';

  const CHAVE = 'pncp-auto-compra';
  const OPCAO = 'todos os relatórios e termos';
  const BOTAO = 'app-botao-relatorios-compra button';
  const ERRO_DOWNLOAD = 'não foi possível realizar o download';
  const PASSO = 150;              // ms entre verificações (1.3: era 500)
  const SEM_BOTAO = 90 * 1000;    // sem o botão depois disso (e sem desafio na tela): desiste
  const SEM_ARQUIVO = 3 * 60 * 1000;  // depois do clique, sem download nem erro: deixa a aba aberta
  const SITUACAO = 1500;          // 1.4: "compra anulada/revogada/cancelada" sem o botão por esse tempo: avisa
  const SITUACAO_SEM_ZIP = /compra (anulada|revogada|cancelada)|não houve registro de (proposta)/;
  const situacaoSemZip = (texto) => {
    const m = texto.match(SITUACAO_SEM_ZIP);
    return m ? (m[1] ? `compra-${m[1]}` : 'sem-propostas') : null;
  };

  // A URL é lida logo no início, antes de o Angular reescrevê-la; a sessionStorage é da aba.
  const params = new URLSearchParams(location.search);
  if (params.get('pncpauto') === '1' && params.get('compra')) {
    sessionStorage.setItem(CHAVE, params.get('compra'));
  }
  const idCompra = sessionStorage.getItem(CHAVE);
  if (!idCompra) return;

  const titulo = (texto) => { document.title = `[PNCP auto] ${texto}`; };
  const normalizar = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const visivel = (el) => !!el && el.getClientRects().length > 0;

  let encerrado = false;
  function encerrar(fechaEm) {
    encerrado = true;
    sessionStorage.removeItem(CHAVE);
    setTimeout(() => window.close(), fechaEm);
  }

  // O que a página mostrava, para ajustar os seletores se o site mudar.
  function diagnostico() {
    const botoes = [...document.querySelectorAll('button')].map((b) => [
      b.getAttribute('aria-label'), b.getAttribute('title'), b.className,
      b.querySelector('i') ? b.querySelector('i').className : '', normalizar(b.textContent).slice(0, 40),
      b.disabled ? 'desabilitado' : '', visivel(b) ? 'visível' : 'oculto'].join(' | '));
    const iframes = [...document.querySelectorAll('iframe')].map((f) => {
      const r = f.getBoundingClientRect();
      return `${(f.src || '').slice(0, 80)} ${Math.round(r.width)}x${Math.round(r.height)}`;
    });
    return [
      `título: ${document.title}`,
      `app-botao-relatorios-compra: ${document.querySelectorAll('app-botao-relatorios-compra').length}`,
      `botões (${botoes.length}):`, ...botoes.slice(0, 60),
      `iframes (${iframes.length}):`, ...iframes,
      'texto da página:', normalizar(document.body.innerText).slice(0, 1500),
    ].join('\n');
  }

  // Três jeitos de achar o botão, do mais específico ao mais geral.
  function acharBotao() {
    const todos = [...document.querySelectorAll('button')];
    const grupos = [
      [...document.querySelectorAll(BOTAO)],
      todos.filter((b) => normalizar(b.getAttribute('aria-label')).startsWith('downloads')),
      todos.filter((b) => b.querySelector('i.fa-download')),
    ];
    for (const grupo of grupos) {
      const botao = grupo.find((b) => !b.disabled && visivel(b));
      if (botao) return botao;
    }
    return null;
  }

  function avisar(motivo) {
    if (encerrado) return;
    titulo(motivo);
    const a = document.createElement('a');
    const texto = `${idCompra}\n${motivo}\n${location.href}\n\n${diagnostico()}\n`;
    a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(texto);
    a.download = `pncp-auto-${idCompra}-${motivo}.txt`;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    a.remove();
    encerrar(3000);
  }

  // O site baixa o zip criando um <a download> no body (blob); basta ver esse elemento aparecer.
  function vigiarDownload() {
    new MutationObserver((registros) => {
      for (const r of registros) {
        for (const no of r.addedNodes) {
          if (!encerrado && no.nodeType === 1 && no.tagName === 'A' && no.hasAttribute('download')
              && !no.download.startsWith('pncp-auto-')) {
            titulo('zip baixado');
            encerrar(5000);
          }
        }
      }
    }).observe(document.body, { childList: true });
  }

  function desafioNaTela() {
    // o hCaptcha invisível só mostra iframe grande quando pede desafio
    return [...document.querySelectorAll('iframe[src*="hcaptcha"]')]
      .some((f) => { const r = f.getBoundingClientRect(); return r.width > 200 && r.height > 200; });
  }

  function opcaoDoMenu() {
    const menus = [...document.querySelectorAll('.p-menu, [role="menu"]')].filter(visivel);
    const itens = menus.flatMap((m) => [...m.querySelectorAll('[role="menuitem"], li')]);
    const alvo = itens.find((li) => normalizar(li.textContent) === OPCAO);
    if (!alvo) return { menuAberto: menus.length > 0 && itens.length > 0, alvo: null };
    const clicavel = alvo.querySelector('.p-menu-item-content, .p-menuitem-link, a') || alvo;
    return { menuAberto: true, alvo: clicavel };
  }

  function erroNaTela() {
    return normalizar(document.body.innerText).includes(ERRO_DOWNLOAD);
  }

  const inicio = Date.now();
  let estado = 'botao';
  let desde = inicio;
  let cliquesNoBotao = 0;
  let situacaoDesde = 0;

  function passo() {
    if (encerrado) return;
    const agora = Date.now();
    const desafio = desafioNaTela();
    if (desafio) titulo('resolva o captcha');

    if (location.pathname.includes('acesso-nao-autorizado')) return avisar('acesso-nao-autorizado');
    if (location.pathname.includes('compra-nao-encontrada')) return avisar('compra-nao-encontrada');

    if (estado === 'botao') {
      const botao = acharBotao();
      if (botao) {
        botao.click();
        cliquesNoBotao += 1;
        estado = 'menu';
        desde = agora;
        if (!desafio) titulo('abrindo o menu');
      } else if (!desafio && !situacaoDesde
                 && situacaoSemZip(normalizar(document.body.innerText))) {
        situacaoDesde = agora;
      } else if (!desafio && situacaoDesde && agora - situacaoDesde > SITUACAO) {
        const situacao = situacaoSemZip(normalizar(document.body.innerText));
        if (situacao) return avisar(situacao);
        situacaoDesde = 0;
      } else if (!desafio && agora - inicio > SEM_BOTAO) {
        return avisar('sem-botao');
      }
    } else if (estado === 'menu') {
      const { menuAberto, alvo } = opcaoDoMenu();
      if (alvo) {
        alvo.click();
        estado = 'download';
        desde = agora;
        if (!desafio) titulo('aguardando o zip');
      } else if (agora - desde > 3000) {
        if (menuAberto) return avisar('sem-opcao');
        if (cliquesNoBotao >= 3) return avisar('sem-botao');
        estado = 'botao';  // o menu não abriu: clica de novo
      }
    } else if (estado === 'download') {
      if (erroNaTela()) return avisar('erro-download');
      if (!desafio && agora - desde > SEM_ARQUIVO) {
        titulo('sem resposta; veja a página');
        return;  // deixa a aba aberta para você ver; o baixar_manual.py conta o tempo-limite
      }
    }
    setTimeout(passo, PASSO);
  }

  function comecar() {
    titulo('carregando');
    vigiarDownload();
    setTimeout(passo, PASSO);
  }

  if (document.body) comecar();
  else document.addEventListener('DOMContentLoaded', comecar);
})();
