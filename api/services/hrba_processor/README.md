# HRBA processor (Tasy SEDE -> Tasy HRBA)

Servico Docker: `hrba-processor-service` (porta 8005).
Fila: `nf.hrba.raw` (publicada pelo extractor quando estabelecimento=HRBA).

## Fluxo

1. Extractor (perfil HRBA) le a **SEDE de homolog/prod do canal HRBA**
   (`ORACLE_HRBA_SEDE_DSN_*`) — **nao** usa `ORACLE_DSN` do PR
2. Publica em `nf.hrba.raw`
3. Este servico valida/insere no **HRBA** (`ORACLE_HRBA_DSN_*`)
4. Se estoque OK no HRBA -> marca `dt_integracao` na SEDE do canal HRBA
5. Status no Postgres (`estabelecimento=HRBA`) para o painel

## Env (homolog completo)

```env
ORACLE_HRBA_ENV=homolog
ORACLE_HRBA_SEDE_DSN_HOMOLOG=...   # SEDE teste (fonte)
ORACLE_HRBA_DSN_HOMOLOG=...        # HRBA teste (destino)
```

`ORACLE_DSN` continua so para Castelo/HRAS/HRT/Ponta Pora (PR).
