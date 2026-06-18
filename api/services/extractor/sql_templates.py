HEADER_NOTES_SQL_TEMPLATE = """
SELECT
    nf.nr_nota_fiscal                                       AS NF,
    nf.cd_cgc_emitente                                      AS FORNECEDOR,
    nf.dt_emissao                                           AS DATANOTA,
    'INTEGRACAO'                                            AS OPERADOR,
    CASE WHEN nf.cd_operacao_nf = 5 THEN 'S' ELSE 'N' END  AS DOACAO,
    nf.cd_serie_nf                                          AS SERIE,
    nf.dt_entrada_saida                                     AS DATAREC,
    nf.vl_descontos                                         AS DESCONTO,
    nf.vl_ipi                                               AS IPI,
    nf.vl_frete                                             AS FRETE,
    nf.nr_sequencia                                         AS NR_SEQUENCIA,
    nf.vl_total_nota                                        AS VALOR_TOTAL_NOTA,
    MAX(nfv.dt_vencimento)                                  AS VENCIMENTO
FROM
    tasy.nota_fiscal nf
LEFT JOIN
    tasy.nota_fiscal_venc nfv ON nf.nr_sequencia = nfv.nr_sequencia
WHERE
    ie_tipo_nota = 'EN'
    AND dt_integracao IS NULL
    AND TO_CHAR(dt_atualizacao_estoque, 'YYYY-MM-DD') >= :dt_atualizacao_estoque_min
    AND TO_CHAR(dt_emissao, 'YYYY-MM-DD') >= :dt_emissao_min
    AND cd_estabelecimento = :cd_estabelecimento
    AND ie_situacao NOT IN (2, 3)
    AND cd_operacao_nf IN ({cd_operacao_nf_filter})
GROUP BY
    nf.nr_nota_fiscal,
    nf.cd_cgc_emitente,
    nf.dt_emissao,
    CASE WHEN nf.cd_operacao_nf = 5 THEN 'S' ELSE 'N' END,
    nf.cd_serie_nf,
    nf.dt_entrada_saida,
    nf.vl_descontos,
    nf.vl_ipi,
    nf.vl_frete,
    nf.nr_sequencia,
    nf.vl_total_nota
"""

HEADER_NOTE_BY_NR_SEQUENCIA_SQL = """
SELECT
    nf.nr_nota_fiscal                                       AS NF,
    nf.cd_cgc_emitente                                      AS FORNECEDOR,
    nf.dt_emissao                                           AS DATANOTA,
    'INTEGRACAO'                                            AS OPERADOR,
    CASE WHEN nf.cd_operacao_nf = 5 THEN 'S' ELSE 'N' END  AS DOACAO,
    nf.cd_serie_nf                                          AS SERIE,
    nf.dt_entrada_saida                                     AS DATAREC,
    nf.vl_descontos                                         AS DESCONTO,
    nf.vl_ipi                                               AS IPI,
    nf.vl_frete                                             AS FRETE,
    nf.nr_sequencia                                         AS NR_SEQUENCIA,
    nf.vl_total_nota                                        AS VALOR_TOTAL_NOTA,
    nf.cd_operacao_nf                                       AS CD_OPERACAO_NF,
    nf.cd_estabelecimento                                   AS CD_ESTABELECIMENTO,
    nf.ie_situacao                                          AS IE_SITUACAO,
    nf.dt_integracao                                        AS DT_INTEGRACAO,
    nf.ie_tipo_nota                                         AS IE_TIPO_NOTA,
    nf.dt_atualizacao_estoque                               AS DT_ATUALIZACAO_ESTOQUE,
    MAX(nfv.dt_vencimento)                                  AS VENCIMENTO
FROM
    tasy.nota_fiscal nf
LEFT JOIN
    tasy.nota_fiscal_venc nfv ON nf.nr_sequencia = nfv.nr_sequencia
WHERE
    nf.nr_sequencia = :nr_sequencia
GROUP BY
    nf.nr_nota_fiscal,
    nf.cd_cgc_emitente,
    nf.dt_emissao,
    CASE WHEN nf.cd_operacao_nf = 5 THEN 'S' ELSE 'N' END,
    nf.cd_serie_nf,
    nf.dt_entrada_saida,
    nf.vl_descontos,
    nf.vl_ipi,
    nf.vl_frete,
    nf.nr_sequencia,
    nf.vl_total_nota,
    nf.cd_operacao_nf,
    nf.cd_estabelecimento,
    nf.ie_situacao,
    nf.dt_integracao,
    nf.ie_tipo_nota,
    nf.dt_atualizacao_estoque
"""


ITEMS_BY_NR_SEQUENCIA_SQL_TEMPLATE = """
SELECT
    mat.cd_material                                         AS CODPROD,
    nfi.vl_unitario_item_nf                                 AS CUNIT,
    nfi.vl_total_item_nf                                    AS VALOR,
    nfi.qt_item_nf                                          AS QTDE_ENTRADA,
    nfi.nr_sequencia                                        AS NR_SEQ_NOTA,
    nfi.nr_item_nf                                          AS NR_ITEM_NF,
    mat.ds_reduzida                                         AS DS_REDUZIDA,
    nfi.vl_liquido                                          AS VL_LIQUIDO
FROM
    tasy.nota_fiscal nf
LEFT JOIN
    tasy.nota_fiscal_item nfi ON nf.nr_sequencia = nfi.nr_sequencia
LEFT JOIN
    tasy.material mat ON nfi.cd_material = mat.cd_material
WHERE
    nf.nr_sequencia = :nr_sequencia
    AND cd_local_estoque NOT IN (104)
    AND nf.cd_operacao_nf NOT IN ({cd_operacao_nf_item_not_in_filter})
"""


LOTS_BY_ITEM_LOTE_SQL = """
SELECT
    cd_lote_fabricacao                                      AS LOTE,
    dt_validade                                             AS DT_VALIDADE,
    tasy.obter_desc_marca(nr_seq_marca)                    AS OBSERVACAO,
    qt_material                                             AS QT_LOTE
FROM
    tasy.nota_fiscal_item_lote
WHERE
    nr_seq_nota = :nr_sequencia
    AND nr_item_nf = :nr_item_nf
"""


LOTS_BY_ITEM_FALLBACK_SQL = """
SELECT
    cd_lote_fabricacao                                      AS LOTE,
    dt_validade                                             AS DT_VALIDADE,
    tasy.obter_desc_marca(nr_seq_marca)                    AS OBSERVACAO,
    qt_item_nf                                              AS QT_LOTE
FROM
    tasy.nota_fiscal_item
WHERE
    nr_sequencia = :nr_sequencia
    AND nr_item_nf = :nr_item_nf
"""


def _format_numeric_filter(values: tuple[int, ...]) -> str:
    if not values:
        raise ValueError("Filtro de cd_operacao nao pode ser vazio.")
    return ", ".join(str(int(v)) for v in values)


def build_header_notes_sql(cd_operacao_nf_in: tuple[int, ...]) -> str:
    return HEADER_NOTES_SQL_TEMPLATE.format(
        cd_operacao_nf_filter=_format_numeric_filter(cd_operacao_nf_in)
    )


def build_items_by_nr_sequencia_sql(cd_operacao_nf_item_not_in: tuple[int, ...]) -> str:
    return ITEMS_BY_NR_SEQUENCIA_SQL_TEMPLATE.format(
        cd_operacao_nf_item_not_in_filter=_format_numeric_filter(
            cd_operacao_nf_item_not_in
        )
    )
