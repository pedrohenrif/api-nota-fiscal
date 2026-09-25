"""SQL Tasy SEDE -> HRBA (portado de GA0016, binds nomeados)."""

SELECT_NOTA_HEADER = """
SELECT
    nf.nr_sequencia                                               AS NR_SEQUENCIA,
    nf.cd_cgc_emitente                                            AS FORNECEDOR,
    nf.dt_emissao                                                 AS DATANOTA,
    nf.dt_atualizacao                                             AS ATUALIZACAO,
    CASE WHEN nf.cd_operacao_nf = 5 THEN 'S' ELSE 'N' END         AS DOACAO,
    nf.cd_serie_nf                                                AS SERIE,
    nf.dt_entrada_saida                                           AS DATAREC,
    nf.vl_descontos                                               AS DESCONTO,
    nf.vl_ipi                                                     AS IPI,
    nf.vl_frete                                                   AS FRETE,
    nf.nr_nota_fiscal                                             AS NF,
    nf.cd_estabelecimento                                         AS ESTABELECIMENTO,
    nf.vl_total_nota                                              AS VALOR_TOTAL_NOTA,
    nf.qt_peso_liquido                                            AS PESO_LIQUIDO,
    nf.qt_peso_bruto                                              AS QT_PESO_BRUTO,
    nf.nm_usuario                                                 AS USUARIO,
    nf.nr_sequencia_nf                                            AS NR_SEQUENCIA_NF,
    nf.cd_cgc                                                     AS CNPJ,
    nf.cd_operacao_nf                                             AS OPERACAO,
    nf.ie_acao_nf                                                 AS ACAO_NF,
    nf.ie_emissao_nf                                              AS EMISSAO_NF,
    nf.ie_tipo_frete                                              AS TIPO_FRETE,
    nf.vl_mercadoria                                              AS VL_MERCADORIA,
    CASE WHEN nf.CD_OPERACAO_NF IN (21,22) THEN 'S' ELSE 'N' END  AS CONSIGNADO,
    nf.ds_observacao                                              AS DS_OBSERVACAO
FROM
    tasy.nota_fiscal nf
WHERE
    nf.nr_sequencia = :nr_sequencia
    AND nf.ie_tipo_nota = 'EN'
"""

SELECT_NOTA_VENC = """
SELECT
    nfv.NR_SEQUENCIA,
    nfv.CD_ESTABELECIMENTO,
    nfv.CD_SERIE_NF,
    nfv.NR_SEQUENCIA_NF,
    nfv.DT_VENCIMENTO,
    nfv.VL_VENCIMENTO,
    nfv.DT_ATUALIZACAO,
    nfv.NM_USUARIO,
    nfv.IE_ORIGEM,
    nfv.CD_CGC_EMITENTE,
    nfv.NR_NOTA_FISCAL
FROM
    tasy.NOTA_FISCAL_VENC nfv
WHERE nfv.nr_sequencia = :nr_sequencia
"""

SELECT_NOTA_ITEM = """
SELECT
    nfi.NR_SEQUENCIA,
    nfi.CD_ESTABELECIMENTO,
    nfi.CD_SERIE_NF,
    nfi.NR_SEQUENCIA_NF,
    nfi.NR_ITEM_NF,
    nfi.QT_ITEM_NF,
    nfi.VL_UNITARIO_ITEM_NF,
    nfi.VL_TOTAL_ITEM_NF,
    nfi.DT_ATUALIZACAO,
    nfi.NM_USUARIO,
    nfi.VL_FRETE,
    nfi.VL_DESCONTO,
    nfi.VL_DESPESA_ACESSORIA,
    nfi.VL_DESCONTO_RATEIO,
    nfi.VL_SEGURO,
    nfi.VL_LIQUIDO,
    nfi.CD_CGC_EMITENTE,
    nfi.CD_NATUREZA_OPERACAO,
    nfi.CD_MATERIAL,
    nfi.CD_PROCEDIMENTO,
    nfi.CD_SETOR_ATENDIMENTO,
    nfi.CD_CONTA,
    nfi.CD_LOCAL_ESTOQUE,
    nfi.DS_OBSERVACAO,
    nfi.QT_PESO_BRUTO,
    nfi.QT_PESO_LIQUIDO,
    nfi.CD_UNIDADE_MEDIDA_COMPRA,
    nfi.QT_ITEM_ESTOQUE,
    nfi.CD_UNIDADE_MEDIDA_ESTOQUE,
    nfi.CD_LOTE_FABRICACAO,
    nfi.DT_VALIDADE,
    nfi.DT_ATUALIZACAO_ESTOQUE,
    nfi.NR_NOTA_FISCAL,
    nfi.CD_CONTA_CONTABIL,
    nfi.NR_SEQ_ITEM_LOTE,
    nfi.NR_SEQ_LOTE_FORNEC,
    nfi.IE_ORIGEM_PROCED,
    nfi.CD_SEQUENCIA_PARAMETRO,
    nfi.CD_CATEGORIA_IVA,
    nfi.CD_PROCEDIMENTO_LOC,
    mat.DS_REDUZIDA AS DS_REDUZIDA
FROM
    tasy.NOTA_FISCAL_ITEM nfi
LEFT JOIN
    tasy.material mat ON nfi.cd_material = mat.cd_material
WHERE
    nfi.nr_sequencia = :nr_sequencia
"""

SELECT_NF_ITEM_LOTE = """
SELECT
    NR_SEQUENCIA,
    DT_ATUALIZACAO,
    NM_USUARIO,
    NR_SEQ_NOTA,
    NR_ITEM_NF,
    DT_VALIDADE,
    QT_MATERIAL,
    CD_LOTE_FABRICACAO,
    DT_ATUALIZACAO_NREC,
    NM_USUARIO_NREC,
    NR_SEQ_MARCA,
    NR_SEQ_LOTE_FORNEC,
    IE_INDETERMINADO,
    CD_BARRA_MATERIAL,
    DS_BARRAS
FROM
    TASY.NOTA_FISCAL_ITEM_LOTE
WHERE
    NR_SEQ_NOTA = :nr_sequencia
"""

SELECT_NR_SEQ_HRBA = """
SELECT
    NR_SEQUENCIA
FROM
    tasy.NOTA_FISCAL
WHERE
    NR_NOTA_FISCAL = :NR_NOTA_FISCAL
    AND CD_CGC_EMITENTE = :CD_CGC_EMITENTE
    AND CD_ESTABELECIMENTO = :CD_ESTABELECIMENTO
    AND CD_SERIE_NF = :CD_SERIE_NF
    AND NR_SEQUENCIA_NF = :NR_SEQUENCIA_NF
"""

INSERT_NF = """
INSERT INTO NOTA_FISCAL (
    nr_sequencia, cd_cgc_emitente, dt_emissao, dt_atualizacao, cd_serie_nf,
    dt_entrada_saida, vl_descontos, vl_ipi, vl_frete, nr_nota_fiscal,
    cd_estabelecimento, vl_total_nota, qt_peso_liquido, qt_peso_bruto, nm_usuario,
    nr_sequencia_nf, cd_cgc, cd_operacao_nf, ie_acao_nf, ie_emissao_nf,
    ie_tipo_frete, vl_mercadoria, cd_condicao_pagamento, dt_contabil, cd_pessoa_fisica,
    vl_seguro, vl_despesa_acessoria, vl_despesa_doc, ds_observacao, nr_nota_referencia,
    cd_serie_referencia, cd_natureza_operacao, dt_atualizacao_estoque, vl_desconto_rateio,
    ie_situacao, nr_ordem_compra, nr_lote_contabil, nr_sequencia_ref, cd_moeda,
    vl_conv_moeda, ie_entregue_bloqueto, ie_tipo_nota, cd_setor_digitacao, nr_danfe,
    nr_seq_forma_pagto, nr_autorizacao, cd_control_code, cd_moeda_estrangeira, vl_conv_estrangeiro
) VALUES (
    tasy.NOTA_FISCAL_SEQ.NEXTVAL,
    :FORNECEDOR, :DATANOTA, :ATUALIZACAO, :SERIE, :DATAREC, :DESCONTO, :IPI, :FRETE, :NF,
    :ESTABELECIMENTO, :VALOR_TOTAL_NOTA, :PESO_LIQUIDO, :QT_PESO_BRUTO, :USUARIO,
    :NR_SEQUENCIA_NF, :CNPJ, :OPERACAO, :ACAO_NF, :IE_EMISSAO_NF, :TIPO_FRETE, :VL_MERCADORIA,
    1, null, null, 0, 0, 0, :DS_OBSERVACAO, null, null, 111, null, 0, '1', null, 0, null,
    1, 0, 'N', 'EN', 61, null, null, null, null, null, null
)
"""

INSERT_NFI = """
INSERT INTO NOTA_FISCAL_ITEM (
    NR_SEQUENCIA, CD_ESTABELECIMENTO, CD_SERIE_NF, NR_SEQUENCIA_NF, NR_ITEM_NF,
    QT_ITEM_NF, VL_UNITARIO_ITEM_NF, VL_TOTAL_ITEM_NF, DT_ATUALIZACAO, NM_USUARIO,
    VL_FRETE, VL_DESCONTO, VL_DESPESA_ACESSORIA, VL_DESCONTO_RATEIO, VL_SEGURO, VL_LIQUIDO,
    NR_NOTA_FISCAL, CD_MATERIAL, CD_CONTA_CONTABIL, CD_UNIDADE_MEDIDA_COMPRA,
    CD_UNIDADE_MEDIDA_ESTOQUE, NR_SEQ_ITEM_LOTE, CD_LOTE_FABRICACAO, CD_LOCAL_ESTOQUE,
    DT_VALIDADE, CD_NATUREZA_OPERACAO, CD_CGC_EMITENTE, CD_PROCEDIMENTO, IE_ORIGEM_PROCED,
    CD_SEQUENCIA_PARAMETRO, CD_CATEGORIA_IVA, CD_PROCEDIMENTO_LOC, DT_ATUALIZACAO_ESTOQUE,
    cd_setor_atendimento, cd_conta, ds_observacao, ds_complemento, qt_peso_bruto,
    qt_peso_liquido, qt_item_estoque, cd_centro_custo, cd_material_estoque, nr_ordem_compra,
    pr_desconto, nr_item_oci, dt_entrega_ordem, nr_seq_conta_financ, nr_seq_proj_rec,
    pr_desc_financ, nr_seq_ordem_serv, nr_atendimento, nr_seq_unidade_adic, nr_seq_proj_gpi,
    nr_seq_etapa_gpi, nr_seq_conta_gpi, nr_contrato, dt_inicio_garantia, dt_fim_garantia,
    nr_seq_marca, nr_seq_orc_item_gpi, nr_solic_compra, nr_item_solic_compra,
    nr_seq_regra_contrato, nr_seq_preco_pj, cd_federal_voucher, vl_unit_estrangeiro,
    vl_total_estrangeiro, nr_serie_material, cd_paciente, nr_seq_concepto_acreencia, vl_desc_financ
) VALUES (
    :NR_SEQUENCIA, :CD_ESTABELECIMENTO, :CD_SERIE_NF, :NR_SEQUENCIA_NF, :NR_ITEM_NF,
    :QT_ITEM_NF, :VL_UNITARIO_ITEM_NF, :VL_TOTAL_ITEM_NF, :DT_ATUALIZACAO, :NM_USUARIO,
    :VL_FRETE, :VL_DESCONTO, :VL_DESPESA_ACESSORIA, :VL_DESCONTO_RATEIO, :VL_SEGURO, :VL_LIQUIDO,
    :NR_NOTA_FISCAL, :CD_MATERIAL, :CD_CONTA_CONTABIL, :CD_UNIDADE_MEDIDA_COMPRA,
    :CD_UNIDADE_MEDIDA_ESTOQUE, :NR_SEQ_ITEM_LOTE, :CD_LOTE_FABRICACAO, :CD_LOCAL_ESTOQUE,
    :DT_VALIDADE, :CD_NATUREZA_OPERACAO, :CD_CGC_EMITENTE, :CD_PROCEDIMENTO, :IE_ORIGEM_PROCED,
    :CD_SEQUENCIA_PARAMETRO, :CD_CATEGORIA_IVA, :CD_PROCEDIMENTO_LOC, :DT_ATUALIZACAO_ESTOQUE,
    null, null, null, null, null, null, :QT_ITEM_ESTOQUE, :CENTRO_CUSTO, :CD_MATERIAL_ESTOQUE,
    null, null, null, null, null, null, 0, null, null, null, null, null, null, null, null,
    null, null, null, null, null, null, null, null, null, null, null, null, 0
)
"""

INSERT_NFIL = """
INSERT INTO NOTA_FISCAL_ITEM_LOTE(
    NR_SEQUENCIA, DT_ATUALIZACAO, NM_USUARIO, NR_SEQ_NOTA, NR_ITEM_NF, DT_VALIDADE,
    QT_MATERIAL, CD_LOTE_FABRICACAO, DT_ATUALIZACAO_NREC, NM_USUARIO_NREC, NR_SEQ_MARCA,
    NR_SEQ_LOTE_FORNEC, IE_INDETERMINADO, CD_BARRA_MATERIAL, DS_BARRAS
) VALUES (
    NOTA_FISCAL_ITEM_LOTE_SEQ.NEXTVAL, SYSDATE, :NM_USUARIO, :NR_SEQUENCIA, :NR_ITEM_NF,
    :DT_VALIDADE_LOTE, :QT_MATERIAL_LOTE, :DS_LOTE_FORNECEDOR, SYSDATE, :NM_USUARIO,
    null, null, :IE_INDETERMINADA, :CD_BARRA_MATERIAL, :DS_BARRAS
)
"""

# Corrigido: usa NR_SEQUENCIA conhecido (nao MAX da tabela).
INSERT_NFV = """
INSERT INTO NOTA_FISCAL_VENC (
    NR_SEQUENCIA, CD_ESTABELECIMENTO, CD_SERIE_NF, NR_SEQUENCIA_NF, DT_VENCIMENTO,
    VL_VENCIMENTO, DT_ATUALIZACAO, NM_USUARIO, NR_NOTA_FISCAL, IE_ORIGEM, CD_CGC_EMITENTE
) VALUES (
    :NR_SEQUENCIA, :CD_ESTABELECIMENTO, :CD_SERIE_NF, :NR_SEQUENCIA_NF, :DT_VENCIMENTO,
    :VL_VENCIMENTO, :DT_ATUALIZACAO, :NM_USUARIO, :NR_NOTA_FISCAL, :IE_ORIGEM, :CD_CGC_EMITENTE
)
"""

UPDATE_DT_INTEGRACAO = """
UPDATE tasy.nota_fiscal
SET dt_integracao = SYSDATE
WHERE nr_sequencia = :nr_sequencia
"""

VALIDAR_INTEGRACAO = """
SELECT DT_ATUALIZACAO_ESTOQUE
FROM NOTA_FISCAL
WHERE NR_SEQUENCIA = :NR_SEQUENCIA
"""

SELECT_LOTE_FORNEC_EXIST = """
SELECT NR_SEQ_LOTE_FORNEC
FROM NOTA_FISCAL_ITEM_LOTE
WHERE NR_SEQ_NOTA = :NR_SEQUENCIA
  AND NR_ITEM_NF = :NR_ITEM_NF
"""

SELECT_NR_ATENDIMENTO = """
SELECT
    NR_DOC_IMPORTACAO AS NR_ATENDIMENTO,
    DT_REG_IMPORTACAO AS DT_ATENDIMENTO
FROM
    tasy.NOTA_FISCAL_ITEM
WHERE
    nr_sequencia = :nr_sequencia
"""

SELECT_MATERIAL = """
SELECT CD_MATERIAL
FROM MATERIAL
WHERE CD_SISTEMA_ANT = :CD_SISTEMA_ANT
"""

SELECT_UNIDADES_MEDIDAS = """
SELECT CD_UNIDADE_MEDIDA_COMPRA, CD_UNIDADE_MEDIDA_ESTOQUE
FROM tasy.material
WHERE CD_MATERIAL = :CD_MATERIAL
"""

SELECT_CONTA_CONTABIL = """
SELECT obter_conta_contabil_material(1, cd_material)
FROM MATERIAL
WHERE CD_MATERIAL = :CD_MATERIAL
"""

SELECT_CGC_EMITENTE = """
SELECT CD_CGC
FROM PESSOA_JURIDICA
WHERE CD_CGC = :cd_cgc
"""
