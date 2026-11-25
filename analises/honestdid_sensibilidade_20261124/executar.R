# HonestDiD (Rambachan e Roth, 2023): sensibilidade do estudo de eventos A × AF. EXPLORATÓRIO (protocolo.md).
#
# Lê entradas/{manifesto,beta,sigma}.csv (gerados por coeficientes.py) e grava, em tabelas/:
#   honestdid_resultados.csv  IC robusto (lb, ub) por especificação, parâmetro, família e valor; IC original do pacote;
#                             conjunto identificado no ponto estimado (funções internas do pacote)
#   honestdid_quebras.csv     menor valor em que o IC passa a incluir zero (só quando no menor valor ele exclui zero)
#   r_ambiente.csv            versões do R e dos pacotes, núcleos e tempo
# Uso, da pasta PNCP-Automation:
#   Rscript analises/honestdid_sensibilidade_20261124/executar.R
# No RStudio: setwd(".../PNCP-Automation"); source("analises/honestdid_sensibilidade_20261124/executar.R")
# Variáveis opcionais: HONESTDID_NUCLEOS (padrão 3); HONESTDID_SO_PRINCIPAL=1 (só a especificação P1, teste rápido).

args <- commandArgs(trailingOnly = TRUE)
PASTA <- if (length(args) >= 1) args[1] else file.path("analises", "honestdid_sensibilidade_20261124")
ENT <- file.path(PASTA, "entradas")
TAB <- file.path(PASTA, "tabelas")
stopifnot(dir.exists(ENT))
dir.create(TAB, showWarnings = FALSE)
suppressPackageStartupMessages(library(HonestDiD))
T0 <- proc.time()[["elapsed"]]

man <- read.csv(file.path(ENT, "manifesto.csv"), stringsAsFactors = FALSE, encoding = "UTF-8")
bet <- read.csv(file.path(ENT, "beta.csv"), stringsAsFactors = FALSE)
sig <- read.csv(file.path(ENT, "sigma.csv"), stringsAsFactors = FALSE)
if (nzchar(Sys.getenv("HONESTDID_SO_PRINCIPAL"))) man <- man[man$espec == "P1", ]
SO_IDS <- Sys.getenv("HONESTDID_SO_IDS")            # refazer só estas linhas (ids separados por vírgula)
SUFIXO <- ""
if (nzchar(SO_IDS)) {
  man <- man[man$id %in% strsplit(SO_IDS, ",")[[1]], ]
  SUFIXO <- "_refeitos"
}
NUC <- as.integer(Sys.getenv("HONESTDID_NUCLEOS", "3"))

# custo esperado (mais pré-períodos e Δ^SDRM primeiro, influência por último), para equilibrar os núcleos
man$custo <- ifelse(man$grade == "loo", 1, 10 * man$numPre * (man$numPre + man$numPost) * (1 + 2 * man$sdrm))
man <- man[order(-man$custo), ]

tarefa <- function(m, bet, sig) {
  suppressPackageStartupMessages(library(HonestDiD))
  ALFA <- 0.05
  MBAR <- c(0, 0.5, 1, 1.5, 2, 3)
  MSD <- c(0, 0.25, 0.5, 1, 1.5, 2, 3)
  TOL <- 0.01
  b <- bet[bet$id == m$espec, ]
  b <- b[order(b$ordem), ]$beta_lp
  n <- length(b)
  s <- sig[sig$id == m$espec, ]
  S <- matrix(NA_real_, n, n)
  S[cbind(s$i, s$j)] <- s$valor_lp2
  stopifnot(!anyNA(S))
  S <- (S + t(S)) / 2
  nPre <- m$numPre
  nPost <- m$numPost
  l <- as.numeric(strsplit(m$l_vec, ";")[[1]])
  stopifnot(length(b) == nPre + nPost, length(l) == nPost)
  post <- (nPre + 1):(nPre + nPost)
  est <- sum(l * b[post])
  sdth <- sqrt(c(t(l) %*% S[post, post] %*% l))
  avisos <- character(0)
  guarda <- function(expr) withCallingHandlers(expr, warning = function(w) {
    avisos <<- c(avisos, conditionMessage(w))
    invokeRestart("muffleWarning")
  })
  inclui0 <- function(lb, ub) !is.na(lb) & !is.na(ub) & lb <= 0 & ub >= 0

  roda <- function(fam, vals) {
    t1 <- proc.time()[["elapsed"]]
    r <- tryCatch(guarda(
      if (fam == "SD") {
        createSensitivityResults(betahat = b, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost,
                                 Mvec = vals, l_vec = l, alpha = ALFA)
      } else {
        createSensitivityResults_relativeMagnitudes(
          betahat = b, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost,
          bound = if (fam == "RM") "deviation from parallel trends" else "deviation from linear trend",
          Mbarvec = vals, l_vec = l, alpha = ALFA)
      }), error = function(e) e)
    seg <- (proc.time()[["elapsed"]] - t1) / length(vals)
    if (inherits(r, "error") && length(vals) > 1) {
      # falha numérica num valor derruba a chamada inteira: reavalia valor a valor
      return(do.call(rbind, lapply(vals, function(v) roda(fam, v))))
    }
    if (inherits(r, "error")) {
      return(data.frame(valor = vals, lb = NA_real_, ub = NA_real_, metodo = NA_character_, delta = NA_character_,
                        erro = conditionMessage(r), segundos = seg))
    }
    r <- as.data.frame(r)
    v <- if ("Mbar" %in% names(r)) r$Mbar else r$M
    data.frame(valor = as.numeric(v), lb = as.numeric(r$lb), ub = as.numeric(r$ub), metodo = r$method,
               delta = r$Delta, erro = "", segundos = seg)
  }

  idset <- function(fam, v) {
    f <- switch(fam, RM = HonestDiD:::.compute_IDset_DeltaRM, SD = HonestDiD:::.compute_IDset_DeltaSD,
                SDRM = HonestDiD:::.compute_IDset_DeltaSDRM)
    r <- tryCatch(guarda(if (fam == "SD") {
      f(M = v, trueBeta = b, l_vec = l, numPrePeriods = nPre, numPostPeriods = nPost)
    } else {
      f(Mbar = v, trueBeta = b, l_vec = l, numPrePeriods = nPre, numPostPeriods = nPost)
    }), error = function(e) NULL)
    if (is.null(r)) return(c(NA_real_, NA_real_))
    c(as.numeric(r$id.lb)[1], as.numeric(r$id.ub)[1])
  }

  quebra <- function(fam, r) {
    r <- r[order(r$valor), ]
    if (is.na(r$lb[1]) || inclui0(r$lb[1], r$ub[1])) {
      return(list(aplica = FALSE, quebra = NA_real_, nota = "IC no menor valor da grade já inclui zero"))
    }
    j <- which(inclui0(r$lb, r$ub))
    if (length(j) == 0) {
      return(list(aplica = TRUE, quebra = Inf, nota = sprintf("exclui zero em toda a grade (até %g)", max(r$valor))))
    }
    lo <- r$valor[j[1] - 1]
    hi <- r$valor[j[1]]
    while (hi - lo > TOL) {
      mid <- (lo + hi) / 2
      x <- roda(fam, mid)
      if (is.na(x$lb[1])) break
      if (inclui0(x$lb[1], x$ub[1])) hi <- mid else lo <- mid
    }
    list(aplica = TRUE, quebra = hi, nota = sprintf("entre %.3f e %.3f", lo, hi))
  }

  t0 <- proc.time()[["elapsed"]]
  o <- guarda(constructOriginalCS(betahat = b, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost,
                                  l_vec = l, alpha = ALFA))
  cab <- list(id = m$id, espec = m$espec, parametro = m$parametro, grade = m$grade, estimativa_lp = est,
              ep_theta_lp = sdth, grade_rm_inf = est - 20 * sdth, grade_rm_sup = est + 20 * sdth)
  res <- list(data.frame(cab, familia = "original", valor = NA_real_, lb = as.numeric(o$lb)[1],
                         ub = as.numeric(o$ub)[1], metodo = "Original", delta = NA_character_, erro = "",
                         segundos = NA_real_, id_lb = est, id_ub = est))
  qb <- list()
  for (fam in c("RM", "SD", if (m$sdrm == 1) "SDRM")) {
    vals <- if (m$grade == "completa") (if (fam == "SD") MSD else MBAR) else 1
    r <- roda(fam, vals)
    ids <- t(vapply(r$valor, function(v) idset(fam, v), numeric(2)))
    r$id_lb <- ids[, 1]
    r$id_ub <- ids[, 2]
    res[[length(res) + 1]] <- data.frame(cab, familia = fam, r)
    if (m$grade == "completa") {
      q <- quebra(fam, r)
      qb[[length(qb) + 1]] <- data.frame(cab, familia = fam, aplica = q$aplica, quebra = q$quebra, nota = q$nota)
    }
  }
  out <- do.call(rbind, res)
  out$avisos_n <- length(avisos)
  out$avisos <- paste(unique(substr(avisos, 1, 80)), collapse = " | ")
  out$segundos_linha <- proc.time()[["elapsed"]] - t0
  list(res = out, qb = if (length(qb)) do.call(rbind, qb) else NULL)
}

linhas <- split(man, seq_len(nrow(man)))
if (NUC > 1 && length(linhas) > 1) {
  cl <- parallel::makeCluster(min(NUC, length(linhas)))
  parallel::clusterCall(cl, function(p) invisible(.libPaths(p)), .libPaths())
  saida <- tryCatch(parallel::parLapplyLB(cl, linhas, tarefa, bet = bet, sig = sig),
                    finally = parallel::stopCluster(cl))
} else {
  saida <- lapply(linhas, tarefa, bet = bet, sig = sig)
}

grava <- function(x, nome) {
  con <- file(file.path(TAB, nome), open = "wb")
  write.csv(x, con, row.names = FALSE)
  close(con)
}
res <- do.call(rbind, lapply(saida, `[[`, "res"))
res$inclui_zero <- with(res, !is.na(lb) & !is.na(ub) & lb <= 0 & ub >= 0)
res$toca_grade_rm <- with(res, familia %in% c("RM", "SDRM") &
                            (abs(lb - grade_rm_inf) < 1e-6 * pmax(1, abs(grade_rm_inf)) |
                               abs(ub - grade_rm_sup) < 1e-6 * pmax(1, abs(grade_rm_sup))))
res <- res[order(res$espec, res$parametro, res$familia, res$valor), ]
grava(res, paste0("honestdid_resultados", SUFIXO, ".csv"))
qb <- do.call(rbind, lapply(saida, `[[`, "qb"))
if (!is.null(qb)) grava(qb[order(qb$espec, qb$parametro, qb$familia), ], paste0("honestdid_quebras", SUFIXO, ".csv"))

pk <- c("HonestDiD", "CVXR", "Rglpk", "lpSolveAPI", "ECOSolveR", "TruncatedNormal", "mvtnorm", "Matrix", "pracma",
        "foreach", "purrr", "dplyr", "tibble")
amb <- data.frame(chave = c("R", "plataforma", paste0("pacote_", pk), "nucleos", "linhas_manifesto", "linhas_com_erro",
                            "avisos_total", "segundos"),
                  valor = c(R.version.string, R.version$platform,
                            vapply(pk, function(p) tryCatch(as.character(packageVersion(p)), error = function(e) "ausente"),
                                   character(1)),
                            NUC, nrow(man), sum(tapply(nzchar(res$erro), res$id, any)),
                            sum(tapply(res$avisos_n, res$id, max)), round(proc.time()[["elapsed"]] - T0, 1)))
grava(amb, paste0("r_ambiente", SUFIXO, ".csv"))
cat(sprintf("HonestDiD %s: %d linhas do manifesto, %d com erro, %.0f s\n", as.character(packageVersion("HonestDiD")),
            nrow(man), sum(tapply(nzchar(res$erro), res$id, any)), proc.time()[["elapsed"]] - T0))
