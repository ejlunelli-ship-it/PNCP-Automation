"""Construção da cesta padronizada de produtos (CATMAT × unidade) a partir do pncp.db.

A seleção usa apenas características dos produtos e sua presença nas compras. Nenhum módulo de
seleção lê preço, desconto, valor estimado, valor homologado ou modo de disputa; o teste
`testes/test_independencia.py` verifica isso no código-fonte.
"""
VERSAO = "1.0.0"
