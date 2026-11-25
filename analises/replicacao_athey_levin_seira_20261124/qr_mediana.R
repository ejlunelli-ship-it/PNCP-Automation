# Regressão mediana na compra (média do índice), robustez 8 do protocolo (nota 15 de Athey, Levin e Seira, 2011).
# Lê o CSV gravado por executar.py (y, af, cnpj, amostra e colunas x_*), grava o CSV de resultados.
# IC por bootstrap de pares por CNPJ (B réplicas, semente fixa), em paralelo.
# Uso: Rscript qr_mediana.R <entrada.csv> <saida.csv> [B] [nucleos]
args <- commandArgs(trailingOnly = TRUE)
ENT <- args[1]
SAI <- args[2]
B <- if (length(args) >= 3) as.integer(args[3]) else 299L
NUC <- if (length(args) >= 4) as.integer(args[4]) else 3L
suppressPackageStartupMessages(library(quantreg))
d <- read.csv(ENT, stringsAsFactors = FALSE)
xcols <- grep("^x_", names(d), value = TRUE)

ajusta <- function(dd, cols) {
  X <- cbind(af = dd$af, as.matrix(dd[, cols, drop = FALSE]))
  X <- X[, apply(X, 2, function(v) length(unique(v)) > 1), drop = FALSE]
  f <- rq.fit(cbind(1, X), dd$y, tau = 0.5, method = "fn")
  unname(f$coefficients[2])
}

linhas <- list()
cl <- parallel::makeCluster(NUC)
parallel::clusterEvalQ(cl, suppressPackageStartupMessages(library(quantreg)))
parallel::clusterSetRNGStream(cl, 20261124)
for (am in unique(d$amostra)) {
  dd <- d[d$amostra == am, ]
  for (esp in c("sem controles", "com X do PS2")) {
    cols <- if (esp == "sem controles") character(0) else xcols
    t0 <- proc.time()[["elapsed"]]
    b <- ajusta(dd, cols)
    idx <- split(seq_len(nrow(dd)), dd$cnpj)
    G <- length(idx)
    parallel::clusterExport(cl, c("dd", "cols", "idx", "G", "ajusta"), envir = environment())
    bs <- unlist(parallel::parLapply(cl, seq_len(B), function(r) {
      s <- unlist(idx[sample.int(G, G, replace = TRUE)], use.names = FALSE)
      tryCatch(ajusta(dd[s, ], cols), error = function(e) NA_real_)
    }))
    ok <- is.finite(bs)
    se <- sd(bs[ok])
    linhas[[length(linhas) + 1]] <- data.frame(
      amostra = am, especificacao = esp, coef_lp = b, ep_bootstrap = se,
      ic95_percentil_inf = unname(quantile(bs[ok], 0.025)), ic95_percentil_sup = unname(quantile(bs[ok], 0.975)),
      ic95_normal_inf = b - 1.96 * se, ic95_normal_sup = b + 1.96 * se, p_normal = 2 * pnorm(-abs(b / se)),
      replicas_validas = sum(ok), B = B, compras = nrow(dd), cnpjs = G, compras_AF = sum(dd$af),
      segundos = proc.time()[["elapsed"]] - t0)
  }
}
parallel::stopCluster(cl)
res <- do.call(rbind, linhas)
res$quantreg <- as.character(packageVersion("quantreg"))
res$R <- R.version.string
con <- file(SAI, open = "wb")
write.csv(res, con, row.names = FALSE)
close(con)
cat("quantreg", as.character(packageVersion("quantreg")), ":", nrow(res), "linhas\n")
