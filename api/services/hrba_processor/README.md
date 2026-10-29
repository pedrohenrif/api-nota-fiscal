# HRBA processor (Tasy SEDE -> Tasy HRBA)

Servico Docker: `hrba-processor-service` (porta 8005).
Fila: `nf.hrba.raw` (publicada pelo extractor quando estabelecimento=HRBA).

## Fluxo

1. Extractor (perfil HRBA) le o **mesmo Oracle do PR** (`ORACLE_DSN`, estab 10)
   — override opcional via `ORACLE_HRBA_SEDE_DSN_*`
2. Publica em `nf.hrba.raw`
3. Este servico valida/insere no **Tasy HRBA** (`ORACLE_HRBA_DSN_*`)
4. Se estoque OK no HRBA -> marca `dt_integracao` na SEDE (mesmo `ORACLE_DSN`)
5. Status no Postgres (`estabelecimento=HRBA`) para o painel

## Env (producao tipico)

```env
ORACLE_DSN=...                     # fonte SEDE (mesmo do PR)
ORACLE_HRBA_ENV=production
ORACLE_HRBA_DSN_PRODUCTION=...     # destino Tasy HRBA
# ORACLE_HRBA_SEDE_DSN_* vazio = usa ORACLE_DSN
```
