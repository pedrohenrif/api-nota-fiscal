# HRBA processor (Tasy SEDE -> Tasy HRBA)

Servico Docker: `hrba-processor-service` (porta 8005).
Fila: `nf.hrba.raw` (publicada pelo extractor quando estabelecimento=HRBA).

## Fluxo

1. Extractor (perfil HRBA, cd_estabelecimento=10) publica em `nf.hrba.raw`
2. Este servico recarrega a nota completa na SEDE (`ORACLE_DSN`)
3. Valida CNPJ + de-para material no HRBA
4. INSERT NF/itens/lotes/venc + procedures Tasy no HRBA
5. Se `dt_atualizacao_estoque` no HRBA preenchida -> marca `dt_integracao` na SEDE
6. Status no Postgres (`nota_processamento`, estabelecimento=HRBA) para o painel

## Env

Ver `api/.env.example` (`ORACLE_HRBA_ENV`, `ORACLE_HRBA_DSN_HOMOLOG`, ...).

Homolog: `ORACLE_HRBA_ENV=homolog` + DSN de teste.
