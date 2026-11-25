"""Etapa 16: especificações de robustez R1–R17 (todas predefinidas no protocolo congelado).

Cada especificação = (desenho, método de pareamento, desfecho/referência, ponderação, horizonte, filtro). Quando a
amostra de eventos muda em relação a R1, isso é registrado (eventos próprios e comparação na amostra comum).
"""

ESPECS = [
    # id, descrição, desenho, método, painel, ycol, ncol, pesos, alvo, censura, filtro, tipo
    ("R1", "M0 institucional, peso igual por evento (PRINCIPAL)", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R2", "M1 (M0 + nível/tendência/dispersão do índice em t−6..t−3)", "principal", "M1", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R3", "propensity score de mudança (caliper 0,2 dp do logit)", "principal", "PS", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R4", "Mahalanobis M0 dentro do caliper do PS", "principal", "PSM", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R5", "M0, peso igual por compra (eventos ∝ compras da tratada no horizonte)", "principal", "M0", "S1", "Yc", "nC", "compra", 0, 0, None, "C1"),
    ("R6", "M0, peso igual por item (índice média de itens; eventos ∝ itens)", "principal", "M0", "S1", "Yi", "nI", "item", 0, 0, None, "C1"),
    ("R7", "M0, somente adoções", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, "adocao", "C1"),
    ("R8", "M0, somente abandonos (escala AF − A)", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, "abandono", "C1"),
    ("R9", "M0, mesmo produto pré (t−2..t−1) e pós (C3)", "principal", "M0", "S1", None, None, "evento", 0, 0, None, "C3"),
    ("R10", "M0, cesta de classes CATMAT fixada no pré (C2)", "principal", "M0", "S1", None, None, "evento", 0, 0, None, "C2"),
    ("R11", "M0, referência A1 original da cesta candidata", "principal", "M0", "S1", "Yc_cesta", "nC_cesta", "evento", 0, 0, None, "C1"),
    ("R12", "M0, referência A1 só com UASGs de regime local estável", "principal", "M0", "S1", "Yc_estl", "nC_estl", "evento", 0, 0, None, "C1"),
    ("R12b", "M0, referência EST_A1 do estudo original (estáveis no período todo)", "principal", "M0", "S1", "Yc_estg", "nC_estg", "evento", 0, 0, None, "C1"),
    ("R13", "janela histórica curta (formação t−4..t−3), M0", "curta", "M0", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R14", "M0, segundo horizonte (t0+1), controles censurados ao sair da origem", "principal", "M0", "S1", "Yc", "nC", "evento", 1, 1, None, "C1"),
    ("R14m", "M0, média de t0 e t0+1 (eventos com os dois horizontes)", "principal", "M0", "S1", "Yc", "nC", "evento", [0, 1], 1, None, "C1"),
    ("R15a", "M0 sem o CNPJ tratado dominante (todas as participações)", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, "sem_top1", "C1"),
    ("R15b", "M0 sem os 3 CNPJs tratados dominantes", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, "sem_top3", "C1"),
    ("R16a", "M0 com 1 controle por evento", "principal", "M0_k1", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R16b", "M0 com até 3 controles por evento", "principal", "M0_k3", "S1", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("R17", "cesta S1+S2, M0 (só sensibilidade de classificação técnica)", "S1S2", "M0", "S1S2", "Yc", "nC", "evento", 0, 0, None, "C1"),
    ("X1", "M0, só trocas persistentes em t0+1 (selecionado pela trajetória)", "principal", "M0", "S1", "Yc", "nC", "evento", 0, 0, "persistentes", "C1"),
    ("X2", "M0, peso inverso ao nº de eventos da mesma UASG", "principal", "M0", "S1", "Yc", "nC", "inv_eventos_uasg", 0, 0, None, "C1"),
    ("X3", "M0, peso igual por órgão (CNPJ)", "principal", "M0", "S1", "Yc", "nC", "orgao", 0, 0, None, "C1"),
    ("X4", "M0, t0+1 com IPW de permanência dos controles (sensibilidade)", "principal", "M0", "S1", "Yc", "nC", "evento", 1, 1, "ipw", "C1"),
]
