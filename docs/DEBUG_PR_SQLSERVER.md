# Debug SQL Server PR — notas fiscais

Consultas de apoio para investigar notas no banco do **PR** (SQL Server), schema `integracao.Estoque`.

Complementa:

- [DEBUG_VM.md](./DEBUG_VM.md) — logs e operação na VM
- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md) — fluxo operacional

Use quando houver suspeita de:

- integração parcial (valor no PR menor que no Tasy/painel);
- NF já existente (`Já existe um lançamento… mesma NF e FORNECEDOR`);
- divergência de itens/lotes entre middleware e PR.

Substitua `'1089761'` pelo número da NF em análise.

---

## Tabelas

| Tabela | Uso |
|--------|-----|
| `Estoque.NF` | Cabeçalho (NF + FORNECEDOR) |
| `Estoque.ProdutoNF` | Itens (`ID_NF` → `NF.ID`) |
| `Estoque.ProdutoNFLote` | Lotes (`ID_Prod` → `ProdutoNF.ID`, `ID_NF` → `NF.ID`) |
| `Estoque.Controle` | Log de processamento (`IDNF` → `NF.ID`) |

### Colunas principais

**NF:** `ID`, `NF`, `FORNECEDOR`, `DATANOTA`, `OPERADOR`, `DOACAO`, `SERIE`, `VENCIMENTO`, `DATAREC`, `DESCONTO`, `IPI`, `FRETE`

**ProdutoNF:** `ID`, `ID_NF`, `CODPROD`, `CUNIT`, `VALOR`, `QTDE_ENTRADA`

**ProdutoNFLote:** `ID`, `ID_NF`, `ID_Prod`, `LOTE`, `VALIDADE`, `LABORATORIO`, `QTDE_LOTE`

**Controle:** `IDNF`, `DataHora`, `Sucesso`, `MsgRetorno`, `CCOMPRAS`, `Processamento`

Observação: o cabeçalho **não** guarda `VALORTOTAL`. O valor integrado é a **soma de `ProdutoNF.VALOR`**.

---

## 1. Cabeçalho

```sql
SELECT
    n.ID,
    n.NF,
    n.FORNECEDOR,
    n.DATANOTA,
    n.OPERADOR,
    n.DOACAO,
    n.SERIE,
    n.VENCIMENTO,
    n.DATAREC,
    n.DESCONTO,
    n.IPI,
    n.FRETE
FROM integracao.Estoque.NF AS n
WHERE n.NF = '1089761';
```

---

## 2. Resumo (qtd itens + soma de valor)

```sql
SELECT
    n.ID,
    n.NF,
    n.FORNECEDOR,
    n.SERIE,
    COUNT(p.ID)           AS qtd_itens_pr,
    SUM(p.VALOR)          AS soma_valor_itens,
    SUM(p.QTDE_ENTRADA)   AS soma_qtde
FROM integracao.Estoque.NF AS n
INNER JOIN integracao.Estoque.ProdutoNF AS p
        ON p.ID_NF = n.ID
WHERE n.NF = '1089761'
GROUP BY n.ID, n.NF, n.FORNECEDOR, n.SERIE;
```

Compare com o painel (soma dos itens / qtd). Se a soma no PR for bem menor, a parcialidade está nos itens gravados.

---

## 3. Itens

```sql
SELECT
    p.ID,
    p.ID_NF,
    p.CODPROD,
    p.CUNIT,
    p.VALOR,
    p.QTDE_ENTRADA
FROM integracao.Estoque.NF AS n
INNER JOIN integracao.Estoque.ProdutoNF AS p
        ON p.ID_NF = n.ID
WHERE n.NF = '1089761'
ORDER BY p.ID;
```

---

## 4. Itens + lotes

```sql
SELECT
    n.NF,
    p.CODPROD,
    p.CUNIT,
    p.VALOR,
    p.QTDE_ENTRADA,
    l.LOTE,
    l.VALIDADE,
    l.LABORATORIO,
    l.QTDE_LOTE
FROM integracao.Estoque.NF AS n
INNER JOIN integracao.Estoque.ProdutoNF AS p
        ON p.ID_NF = n.ID
LEFT JOIN integracao.Estoque.ProdutoNFLote AS l
       ON l.ID_Prod = p.ID
      AND l.ID_NF = n.ID
WHERE n.NF = '1089761'
ORDER BY p.ID, l.ID;
```

---

## 5. Controle / retorno do processamento

```sql
SELECT
    c.IDNF,
    c.DataHora,
    c.Sucesso,
    c.Processamento,
    c.CCOMPRAS,
    c.MsgRetorno
FROM integracao.Estoque.NF AS n
INNER JOIN integracao.Estoque.Controle AS c
        ON c.IDNF = n.ID
WHERE n.NF = '1089761'
ORDER BY c.DataHora DESC;
```

---

## 6. Duplicidade de lançamento (mesma NF)

A chave de negócio no PR costuma ser **NF + FORNECEDOR**.

```sql
SELECT
    n.ID,
    n.NF,
    n.FORNECEDOR,
    n.SERIE,
    n.DATANOTA,
    n.OPERADOR
FROM integracao.Estoque.NF AS n
WHERE n.NF = '1089761'
ORDER BY n.ID;
```

Se houver mais de uma linha, rode o **resumo (§2) por `n.ID`** — a “metade” do valor pode ser só um dos lançamentos.

---

## 7. Conferência rápida no Tasy (Oracle) — origem

```sql
-- Cabeçalho
SELECT
    nf.nr_sequencia,
    nf.nr_nota_fiscal,
    nf.cd_cgc_emitente,
    nf.cd_serie_nf,
    nf.vl_total_nota,
    nf.dt_integracao,
    nf.cd_estabelecimento
FROM tasy.nota_fiscal nf
WHERE nf.nr_sequencia = 75660;   -- troque pela sequência

-- Soma dos itens elegíveis (mesmo filtro do integrador: local <> 104)
SELECT
    COUNT(*) AS qtd_itens,
    SUM(NVL(nfi.vl_liquido, nfi.vl_total_item_nf)) AS soma_liquido
FROM tasy.nota_fiscal_item nfi
WHERE nfi.nr_sequencia = 75660
  AND nfi.cd_local_estoque NOT IN (104);
```

---

## 8. Conferência no Postgres do middleware

```sql
SELECT
    id,
    estabelecimento,
    nf,
    nr_sequencia,
    status,
    pr_id,
    pr_mensagem,
    erro,
    updated_at
FROM nota_processamento
WHERE nr_sequencia = '75660'
   OR nf = '1089761'
ORDER BY id DESC;
```

---

## Checklist de leitura

1. Quantas linhas em `Estoque.NF` para aquele número?
2. `COUNT` / `SUM(VALOR)` em `ProdutoNF` bate com o painel?
3. Há lotes em `ProdutoNFLote` para todos os itens que exigem lote?
4. `Controle.MsgRetorno` / `Sucesso` indicam falha parcial?
5. No Tasy, `vl_total_nota` e soma dos itens elegíveis batem com o que enviamos?
