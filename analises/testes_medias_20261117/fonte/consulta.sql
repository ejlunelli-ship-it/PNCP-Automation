SELECT i.id,i.numero_controle_pncp compra,i.numero_item item,c.id_compra,
      c.modo_disputa modo,i.uasg_item uasg,c.uasg uasg_compra,c.orgao_cnpj orgao,c.uf,c.esfera,
      i.cod_item_catalogo codigo,i.codigo_pdm pdm,i.codigo_classe classe,
      i.unidade_medida unidade,i.descricao_resumida descricao,i.criterio_julgamento criterio,
      i.quantidade q,i.valor_unitario_estimado r,i.valor_unitario_resultado p,
      i.orcamento_sigiloso sigilo,c.srp,i.tipo_beneficio beneficio,i.numero_grupo grupo,
      c.data_abertura_proposta abertura,i.data_resultado resultado,i.data_atualizacao atualizado
      FROM compras c CROSS JOIN itens i ON i.numero_controle_pncp=c.numero_controle_pncp
      WHERE c.fonte='dados_abertos' AND c.modalidade_nome LIKE 'Preg%Eletr%'
      AND c.modo_disputa IN ('Aberto','Aberto-Fechado','Fechado-Aberto')
      AND i.registro_principal=1 AND i.material_ou_servico='M'
      AND i.homologado=1 AND i.situacao_item='Homologado'
