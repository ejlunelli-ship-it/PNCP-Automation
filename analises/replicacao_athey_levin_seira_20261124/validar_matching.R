# Conferência do matching (variante a) com o pacote Matching (Sekhon), função Match: M = 4, empates, reposição,
# Var.calc = 4 (variância robusta de Abadie e Imbens com 4 vizinhos do mesmo modo). Protocolo, seção 9.
# Uso: Rscript validar_matching.R <entrada.csv> <saida.csv>   (entrada: y, af, ps, peso)
args <- commandArgs(trailingOnly = TRUE)
suppressPackageStartupMessages(library(Matching))
d <- read.csv(args[1])
linhas <- list()
for (est in c("ATE", "ATT", "ATC")) {
  for (pesos in c("iguais", "itens")) {
    w <- if (pesos == "iguais") rep(1, nrow(d)) else d$peso
    for (amostra_var in c(FALSE, TRUE)) {
      t0 <- proc.time()[["elapsed"]]
      m <- Match(Y = d$y, Tr = d$af, X = d$ps, estimand = est, M = 4, ties = TRUE, replace = TRUE, Var.calc = 4,
                 weights = w, sample = amostra_var, distance.tolerance = 1e-12, version = "standard")
      linhas[[length(linhas) + 1]] <- data.frame(
        estimando = est, pesos = pesos, variancia = if (amostra_var) "condicional (sample = TRUE)" else "populacional",
        est = unname(m$est), se = unname(m$se), se_standard = unname(m$se.standard), n_tratadas = m$wnobs,
        segundos = proc.time()[["elapsed"]] - t0)
    }
  }
}
res <- do.call(rbind, linhas)
res$Matching <- as.character(packageVersion("Matching"))
con <- file(args[2], open = "wb")
write.csv(res, con, row.names = FALSE)
close(con)
cat("Matching", as.character(packageVersion("Matching")), ":", nrow(res), "linhas\n")
