# HonestDiD (Rambachan e Roth, 2023) sobre o estudo de eventos dCDH da cesta padronizada. EXPLORATÓRIO.
# Entradas (geradas por em/honest.py): <pasta>/entradas/{manifesto,beta,sigma}.csv
# Saída: <pasta>/honestdid_r.csv (IC robusto por especificação, família e valor) e <pasta>/honestdid_r_ambiente.csv
# Uso: Rscript honestdid.R <pasta>
# A matriz de covariância de cada especificação vem do bootstrap por CNPJ DAQUELA especificação.
# Os valores de M̄ e M são fixados em config.json antes dos resultados; nenhuma escolha posterior.
args <- commandArgs(trailingOnly = TRUE)
PASTA <- if (length(args) >= 1) args[1] else "honestdid_entradas"
ENT <- file.path(PASTA, "entradas")
suppressPackageStartupMessages(library(HonestDiD))
man <- read.csv(file.path(ENT, "manifesto.csv"), stringsAsFactors = FALSE)
bet <- read.csv(file.path(ENT, "beta.csv"), stringsAsFactors = FALSE)
sig <- read.csv(file.path(ENT, "sigma.csv"), stringsAsFactors = FALSE)
MBAR <- as.numeric(strsplit(man$mbar[1], ";")[[1]])
MSD <- as.numeric(strsplit(man$msd[1], ";")[[1]])
saida <- list()
for (k in seq_len(nrow(man))) {
  m <- man[k, ]
  b <- bet[bet$id == m$id, ]
  b <- b[order(b$ordem), ]$beta
  n <- length(b)
  s <- sig[sig$id == m$id, ]
  S <- matrix(NA_real_, n, n)
  S[cbind(s$i, s$j)] <- s$valor
  S <- (S + t(S)) / 2
  l <- as.numeric(strsplit(m$l_vec, ";")[[1]])
  nPre <- m$numPre; nPost <- m$numPost
  est <- sum(l * b[(nPre + 1):(nPre + nPost)])
  orig <- tryCatch(constructOriginalCS(betahat = b, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost, l_vec = l),
                   error = function(e) NULL)
  if (!is.null(orig)) saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "original", valor = NA,
                                                                 lb = orig$lb, ub = orig$ub, estimativa = est, erro = "")
  rm <- tryCatch(createSensitivityResults_relativeMagnitudes(betahat = b, sigma = S, numPrePeriods = nPre,
                 numPostPeriods = nPost, l_vec = l, Mbarvec = MBAR), error = function(e) e)
  if (inherits(rm, "error")) {
    saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "RM", valor = NA, lb = NA, ub = NA, estimativa = est,
                                             erro = conditionMessage(rm))
  } else {
    saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "RM", valor = rm$Mbar, lb = rm$lb, ub = rm$ub,
                                             estimativa = est, erro = "")
  }
  if (nPre >= 2) {
    sd <- tryCatch(createSensitivityResults(betahat = b, sigma = S, numPrePeriods = nPre, numPostPeriods = nPost,
                   l_vec = l, Mvec = MSD), error = function(e) e)
    if (inherits(sd, "error")) {
      saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "SD", valor = NA, lb = NA, ub = NA, estimativa = est,
                                               erro = conditionMessage(sd))
    } else {
      saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "SD", valor = sd$M, lb = sd$lb, ub = sd$ub,
                                               estimativa = est, erro = "")
    }
  } else {
    saida[[length(saida) + 1]] <- data.frame(id = m$id, familia = "SD", valor = NA, lb = NA, ub = NA, estimativa = est,
                                             erro = "nao calculado: menos de 2 periodos previos")
  }
}
out <- do.call(rbind, saida)
write.csv(out, file.path(PASTA, "honestdid_r.csv"), row.names = FALSE)
write.csv(data.frame(R = R.version.string, HonestDiD = as.character(packageVersion("HonestDiD"))),
          file.path(PASTA, "honestdid_r_ambiente.csv"), row.names = FALSE)
