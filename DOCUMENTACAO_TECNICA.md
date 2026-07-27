# Documentação Técnica — Integração de Notas Fiscais (Tasy → PR)

Documento para desenvolvedores. Complementa:

- [api/README.md](./api/README.md)
- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md)
- [OPERACAO_SCHEDULER_E_EMAIL.md](./OPERACAO_SCHEDULER_E_EMAIL.md)
- [DEPLOY_NGINX_HTTP.md](./DEPLOY_NGINX_HTTP.md)
- [GO_LIVE_PRODUCAO.md](./GO_LIVE_PRODUCAO.md)
- [DEBUG_VM.md](./DEBUG_VM.md)
- Manual do cliente: `docs/Manual_Cliente_Painel_Integracao_Notas_Fiscais.docx`

Versão: 1.0 — Julho/2026

---

## 1. Objetivo técnico

Integrar notas fiscais de entrada do **Oracle Tasy** com a API do **PR**, com:

- Extração periódica ou manual
- Processamento assíncrono via RabbitMQ
- Persistência operacional em PostgreSQL
- Painel web (JWT) para operação e auditoria
- Relatório por e-mail
- Write-back de `dt_integracao` no Tasy após sucesso no PR

---

## 2. Arquitetura

```text
[Oracle Tasy]
      │
      ▼
[extractor-service :8001] ──publish──► [RabbitMQ nf.raw]
                                              │
                                              ▼
                                    [processor-service :8002]
                                              │
                     ┌────────────────────────┼────────────────────────┐
                     ▼                        ▼                        ▼
              [PostgreSQL]              [PR API /NF]          [extractor /marcar-integrada]
              nota_processamento         AccessToken            dt_integracao = SYSDATE
                     ▲
                     │
[site React] ──► [web-api-service :8003] ──► extractor / report
                                              │
                                    [report-service :8004] ──SMTP──► e-mail

Opcional (produção HTTP):
  nginx :5001
    /      → site/dist
    /api/  → 127.0.0.1:8003
```

| Serviço Docker | Porta | Pasta |
|----------------|-------|--------|
| `db` | 5432 | Postgres 15 |
| `rabbitmq` | 5672 / UI 15672 | Filas |
| `extractor-service` | 8001 | `api/services/extractor/` |
| `processor-service` | 8002 | `api/services/processor/` |
| `web-api-service` | 8003 | `api/services/web_api/` |
| `report-service` | 8004 | `api/services/report/` |

Filas padrão:

- `RABBITMQ_QUEUE_RAW_NF=nf.raw`
- `RABBITMQ_QUEUE_DEAD=nf.dead`

Shared:

- `api/services/common/` — estabelecimentos, `estabelecimento_config`, destinatários de e-mail

Compose: `api/docker-compose.yml`  
Imagem: `api/docker/Dockerfile` (Python 3.11 + suporte Instant Client)

---

## 3. Estrutura de pastas (mapa crítico)

```text
projeto-nota-fiscal/
├── api/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── requirements.txt
│   ├── docker/Dockerfile
│   └── services/
│       ├── common/
│       │   ├── estabelecimentos.py
│       │   ├── estab_config.py
│       │   └── report_recipients.py
│       ├── extractor/
│       │   ├── main.py                 # FastAPI + scheduler
│       │   ├── extractor.py            # extract / consult / mark integrated
│       │   ├── sql_templates.py        # SQL Oracle + UPDATE dt_integracao
│       │   ├── extraction_profiles.py  # cd_estabelecimento + filtros
│       │   ├── schemas.py              # payload canônico PR
│       │   ├── publisher.py            # → nf.raw
│       │   └── oracle_*.py
│       ├── processor/
│       │   ├── main.py                 # sobe consumer thread
│       │   ├── consumer.py             # retry / DLQ / orquestra writeback
│       │   ├── depara.py
│       │   ├── dispatcher.py           # POST /NF
│       │   ├── pr_payload.py / pr_response.py
│       │   ├── error_tipo.py
│       │   ├── models.py / repository.py / migrations.py
│       │   └── tasy_writeback.py
│       ├── web_api/
│       │   ├── main.py                 # rotas do painel
│       │   ├── security.py / deps.py
│       │   ├── audit.py / panel_data.py
│       │   └── models.py / schemas.py
│       └── report/
│           ├── main.py / service.py / classifier.py
│           ├── email_html.py / smtp_client.py
│           └── report_sent.py          # envio único
├── site/src/                           # React + Vite + TypeScript
├── deploy/nginx-isms-nf.conf
└── docs/                               # manuais gerados
```

---

## 4. Fluxo ponta a ponta

### 4.1 Triggers

| Origem | Como |
|--------|------|
| Automático | Scheduler do extractor (`EXTRACTION_SCHEDULER_ENABLED` + `estabelecimento_config.scheduler_enabled`) a cada `POLL_INTERVAL_MINUTES` (padrão 6) |
| Manual pendentes | Site → `POST /notas/emitir` → extractor `POST /run` |
| Manual específica | Site → `POST /notas/emitir-especifica` → extractor |
| Reemissão | Site → `POST /notas/reemitir` (só `retry_pending` / `dead_letter`) |

Emissão manual **não depende** dos toggles de scheduler.

### 4.2 Extração

1. Lê perfil em `extraction_profiles.py` (`cd_estabelecimento`, operações, datas).
2. SQL em `sql_templates.py` (sempre prefixar colunas `nf.` / `nfi.` — evita `ORA-00918`).
3. Filtros típicos: `dt_integracao IS NULL`, `ie_tipo_nota = 'EN'`, ops `1,39`, item op `33` excluída,
   `dt_atualizacao_estoque` com **janela móvel de 31 dias** (`hoje - 31`, recalculada a cada extração),
   e `dt_emissao` mínima fixa no perfil.
4. Monta `NotaFiscalPRPayload` e publica JSON durable em `nf.raw`.

### 4.3 Processamento

Arquivo: `processor/consumer.py`

1. Consome mensagem.
2. Se já existe registro `sent` para a mesma chave → ignora (idempotência).
3. `apply_depara_rules` — valida vínculo Tasy↔PR.
4. `send_to_pr` — `POST {base}/NF`.
5. Sucesso → upsert `status=sent` + write-back Tasy.
6. Falha → classifica `erro_tipo`, incrementa tentativas; até `MAX_PROCESSING_RETRIES` (3) reencaminha com delay; senão `dead_letter` + publica em `nf.dead`.

### 4.4 Write-back `dt_integracao`

```text
processor/tasy_writeback.py
  → POST extractor /notas/marcar-integrada?nr_sequencia=
  → UPDATE tasy.nota_fiscal SET dt_integracao = SYSDATE
       WHERE nr_sequencia = :nr AND dt_integracao IS NULL
```

Se o write-back falhar após PR OK: nota permanece `sent` e o alerta vai em `pr_mensagem`.  
Oracle user precisa de **UPDATE** em `tasy.nota_fiscal.dt_integracao`.

---

## 5. Estabelecimentos (códigos Tasy)

| Nome | `cd_estabelecimento` |
|------|----------------------|
| Castelo | 8 |
| HRAS | 9 |
| HRT | 7 |
| Ponta Pora | 16 |

Definidos em `api/services/common/estabelecimentos.py` e `extraction_profiles.py`.

---

## 6. Contrato com o PR

### 6.1 HTTP

- Método: `POST {PR_BASE_URL}/NF`
- `PR_BASE_URL_*` deve terminar em `/PREstAPI` **sem** `/NF`
- Header de auth: `AccessToken: <token>` (não Bearer) — `processor/config.py`
- Ambiente: `PR_ENV=homolog|production`
  - Homolog: token único `PR_HOMOLOG_TOKEN`
  - Production: token por unidade (`PR_CASTELO_TOKEN`, etc.)

### 6.2 Payload

JSON **flat camelCase** (sem wrapper `{ "nota": ... }`).

Campos principais (ver `extractor/schemas.py` + normalização em `processor/pr_payload.py`):

- Cabeçalho: `nf`, `serie`, `fornecedor.cnpj`, `dataNF`, `operador`, `doacao`, `vencimento`, `dataRecebimento`, `desconto`, `ipi`, `frete`, `valorTotal`, `qtdItens`
- Produtos: `codProd`, `cunit`, `valor`, `qtdEntrada`, `loteNF[]`
- Lote: `lote`, `validade?`, `observacao` (default `"-"`), `qtdLote` como **int**
- Removidos no POST: `estabelecimento`, `nrSequencia`, campos `_…`, helpers de de-para

### 6.3 De-para

Arquivo: `processor/depara.py`

1. `GET {base}/Controle/produtos/{codVinculo}` com **código Tasy**
2. Valida existência do vínculo
3. No POST `/NF`, `codProd` enviado é o **código Tasy** (`Cd_Integracao`), não o `CodProd` interno do PR
4. Campos auxiliares (`depara`, `codProdPR`, etc.) são removidos antes do envio

### 6.4 Resposta PR

`processor/pr_response.py`: sucesso quando `sucesso: true` (persistir `pr_id` / `pr_mensagem`).

---

## 7. Modelo de dados (PostgreSQL)

### 7.1 `usuario`

Login do painel. Roles: `adm` | `usuario`.  
Admin: `estabelecimento` null. Usuário: estabelecimento obrigatório.

### 7.2 `nota_processamento`

Status operacional da integração.

| Coluna | Uso |
|--------|-----|
| `estabelecimento`, `nf`, `nr_sequencia` | Chaves de negócio |
| `status` | `pending` / `sent` / `retry_pending` / `dead_letter` |
| `tentativas` | Contador |
| `erro`, `erro_tipo` | Último erro + classificação |
| `pr_id`, `pr_mensagem` | Retorno PR / alertas |
| `created_at`, `updated_at` | Auditoria / lookback e-mail |

Migrations aditivas: `processor/migrations.py`.

### 7.3 `estabelecimento_config`

| Coluna | Uso |
|--------|-----|
| `scheduler_enabled` | Extração automática da unidade |
| `report_enabled` | E-mail automático da unidade |

### 7.4 `access_audit_log`

Auditoria HTTP do painel (IP, user, action, path, status).  
IP respeita `X-Forwarded-For` / `X-Real-IP` (nginx).

### 7.5 `report_destinatario`

CRUD de e-mails por estabelecimento. Seed inicial a partir de `REPORT_EMAIL_*` se a tabela estiver vazia.

### 7.6 `nota_report_envio`

Deduplicação de seções do e-mail:

- Envio único: `integradas`, `erros_pr`, `nao_integradas`
- Podem repetir: `sem_depara`, `sem_lote`

---

## 8. APIs por serviço

### 8.1 web-api `:8003`

| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/health` | — | Health |
| POST | `/auth/login` | — | JWT |
| GET | `/auth/me` | Bearer | Usuário atual |
| GET | `/estabelecimentos` | Bearer | Lista unidades do perfil |
| GET | `/dashboard/resumo` | Bearer | KPIs |
| GET | `/dashboard/export` | Bearer | CSV |
| GET/POST | `/usuarios` | Admin | CRUD users |
| POST | `/notas/emitir` | Bearer | Pendentes |
| GET | `/notas/consultar` | Bearer | Consulta Tasy |
| POST | `/notas/emitir-especifica` | Bearer | Por `nr_sequencia` |
| POST | `/notas/reemitir` | Bearer | Retry/DLQ |
| GET | `/notas` | Bearer | Lista paginada |
| GET | `/notas/{id}/detalhe` | Bearer | Detalhe + preview/de-para |
| GET | `/admin/logs` | Admin | Logs processamento |
| GET | `/admin/acesso` | Admin | Auditoria |
| GET | `/admin/acesso/resumo` | Admin | Resumo IPs |
| GET/POST/PATCH/DELETE | `/destinatarios` | Bearer | E-mails relatório |
| GET/PATCH | `/admin/estabelecimentos/.../config` | Admin | Toggles |
| POST | `/admin/relatorios/enviar` | Admin | Proxy → report |

Query params relevantes em `/notas`: filtros + `ordenacao=nr_sequencia|data_nf` + `page` + `page_size`.

### 8.2 extractor `:8001`

| Método | Path |
|--------|------|
| GET | `/health` |
| POST | `/run?estabelecimento=` |
| GET | `/preview?estabelecimento=` |
| GET | `/notas/consultar` |
| POST | `/notas/emitir-especifica` |
| POST | `/notas/marcar-integrada?nr_sequencia=` |

### 8.3 processor `:8002`

| Método | Path |
|--------|------|
| GET | `/health` | inclui `consumer_running` |
| POST | `/consume` | processa 1 mensagem (debug); loop sobe no startup |

### 8.4 report `:8004`

| Método | Path |
|--------|------|
| GET | `/health` |
| POST | `/relatorios/enviar?estabelecimento=` |
| POST | `/relatorios/ciclo` |

---

## 9. Classificação de erros e retries

Arquivo: `processor/error_tipo.py`

| `erro_tipo` | Heurística (tokens na mensagem) |
|-------------|----------------------------------|
| `sem_depara` | de-para, depara, sem vinculo, vazio no pr… |
| `sem_lote` | sem lote, lotenf, observacao field is required, lote+obrigat… |
| `retorno_pr` | pr http, pr:, ja integrada, produto informado… |
| `outro` | fallback |

Retries:

- `MAX_PROCESSING_RETRIES` (default 3)
- `RETRY_DELAY_SECONDS` (default 10)
- Após esgotar → `dead_letter` + fila `nf.dead`

---

## 10. Relatório por e-mail

Arquivos: `report/classifier.py`, `service.py`, `report_sent.py`

Ciclo: `REPORT_INTERVAL_MINUTES` (30)  
Lookback middleware: `REPORT_LOOKBACK_MINUTES`  
Master: `REPORT_SCHEDULER_ENABLED`  
Por unidade: `estabelecimento_config.report_enabled`

Classificação:

1. Integradas (`sent` recentes) — **uma vez**
2. Erros PR (`retry_pending`/`dead_letter` recentes) — **uma vez**
3. Oracle elegíveis não `sent`:
   - sem de-para (repete)
   - senão sem lote (repete)
   - senão não integrada (uma vez)

SMTP: `SMTP_*` + fallback `SMTP_*_FALLBACK`.

---

## 11. Frontend (`site/`)

Stack: React 18 + Vite + TypeScript + React Router.

| Arquivo | Função |
|---------|--------|
| `src/api.ts` | `VITE_API_BASE_URL`, Bearer, token `isms_nf_token` |
| `src/auth.tsx` | Login / me / logout |
| `src/App.tsx` | Rotas |
| `src/pages/EmitirNota.tsx` | Emissão + lista |
| `src/pages/Dashboard.tsx` | KPIs + CSV |
| `src/pages/Destinatarios.tsx` | CRUD e-mails |
| `src/pages/Configuracoes.tsx` | Toggles Admin |
| `src/pages/Logs.tsx` / `Acesso.tsx` | Admin |
| `src/pages/Usuarios.tsx` | Admin |
| `src/pages/Ajuda.tsx` | Help |

JWT claims: `sub`, `role`, `estabelecimento`, `exp` (`JWT_EXPIRE_MINUTES`, default 480).

Build:

```bash
cd site
# .env
VITE_API_BASE_URL=http://host:porta/api   # se nginx com /api
# ou
VITE_API_BASE_URL=http://host:8003        # acesso direto à API
npm run build
```

`VITE_*` é embutido no build — mudar URL exige rebuild.

---

## 12. Variáveis de ambiente (referência)

Ver `api/.env.example`. Principais grupos:

| Grupo | Variáveis |
|-------|-----------|
| Extração | `POLL_INTERVAL_MINUTES`, `EXTRACTION_SCHEDULER_ENABLED`, `EXTRACTION_RUN_ON_STARTUP`, `USE_MOCK_ORACLE` |
| Oracle | `ORACLE_DSN`, `ORACLE_CLIENT_LIB_DIR`, `ORACLE_HOST_CLIENT_DIR` |
| Mensageria | `RABBITMQ_URL`, `RABBITMQ_QUEUE_RAW_NF`, `RABBITMQ_QUEUE_DEAD` |
| Postgres | `POSTGRES_URL` |
| PR | `PR_ENV`, `PR_BASE_URL_HOMOLOG`, `PR_BASE_URL_PRODUCTION`, tokens |
| Web | `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, `BOOTSTRAP_ADMIN_*`, `EXTRACTOR_URL`, `REPORT_URL` |
| Report | `REPORT_SCHEDULER_ENABLED`, `REPORT_INTERVAL_MINUTES`, `REPORT_LOOKBACK_MINUTES`, `SMTP_*`, `REPORT_EMAIL_*` |

No Compose, hosts internos (`db`, `rabbitmq`, `extractor-service`, `report-service`) sobrescrevem URLs de serviço.

---

## 13. Docker — operação local / VM

```bash
cd api
cp .env.example .env   # editar
docker compose up -d
docker compose ps
docker compose logs -f extractor-service processor-service web-api-service
```

Healthchecks:

```bash
curl -s http://localhost:8001/health
curl -s http://localhost:8002/health
curl -s http://localhost:8003/health
curl -s http://localhost:8004/health
```

Volumes: código montado em `./:/app` (hot reload por restart). Postgres em volume `pgdata`.

Produção com nginx: preferir `127.0.0.1:8003:8003` no web-api e proxy `/api/`.

---

## 14. Deploy HTTP (nginx + DDNS)

Ver [DEPLOY_NGINX_HTTP.md](./DEPLOY_NGINX_HTTP.md) e `deploy/nginx-isms-nf.conf`.

Pontos críticos:

1. `CORS_ORIGINS` = origem exata do browser (incluir porta se houver, ex. `:5001`)
2. `VITE_API_BASE_URL=http://host:5001/api` + `npm run build`
3. `proxy_pass http://127.0.0.1:8003/;` com barra final (strip `/api`)
4. Permissão de leitura do `site/dist` para o user do nginx (`www-data`) — `chmod 755` na cadeia do `$HOME` se necessário
5. Headers `X-Forwarded-For` / `X-Real-IP` para auditoria correta de IP

---

## 15. Gotchas conhecidos

| Sintoma | Causa / fix |
|---------|-------------|
| `ORA-00918` | Coluna ambígua em JOIN — prefixar `nf.` / `nfi.` em `sql_templates.py` |
| Scheduler “morre” | Exceção não tratada na thread — extrator já envolve ciclos em try/except |
| PR 400 payload | Wrapper `{nota}`, `qtdLote` float, `observacao` null |
| De-para “ok” mas PR rejeita | Confirmar que POST usa código Tasy |
| Nota reaparece na fila | `dt_integracao` não atualizou no Tasy após `sent` |
| Site chama `localhost:8003` em produção | Rebuild com `VITE_API_BASE_URL` correto |
| CORS no browser | `CORS_ORIGINS` sem a origem/porta exata |
| Nginx 500 no `/` | Permission denied no `dist` sob `/home/...` |
| Nginx não sobe | Porta 80 ocupada (Apache) — desabilitar `default` e usar só `listen 5001` |
| Instant Client / `DPI-1047` / `libaio` | Rebuild imagem + mount do client |
| `git pull` bloqueado por `tsbuildinfo` | Arquivo de cache TS — `git restore` / deixar de versionar |

---

## 16. Auth e autorização

- Login: `POST /auth/login` → JWT HS256
- Dependências: `get_current_user`, `require_admin` em `web_api/deps.py`
- Middleware de audit em `web_api/main.py` + log especial de login
- Escopo de dados: não-admin forçado ao `current_user.estabelecimento`

Senhas: bcrypt (`security.py`), truncagem estável a 72 bytes.

---

## 17. Como adicionar / alterar comportamentos

| Necessidade | Onde mexer |
|-------------|------------|
| Novo filtro SQL / operação | `sql_templates.py` + `extraction_profiles.py` |
| Novo campo no payload PR | `extractor/schemas.py` + `pr_payload.py` |
| Regra de de-para | `processor/depara.py` |
| Novo tipo de erro | `processor/error_tipo.py` + labels no `site/src/types.ts` |
| Nova rota do painel | `web_api/main.py` + página em `site/src/pages` |
| Seção de e-mail | `report/classifier.py` + `email_html.py` + `report_sent.py` |
| Novo estabelecimento | `estabelecimentos.py`, profiles, tokens PR, seed config, e-mails |

---

## 18. Checklist de onboarding de um novo dev

1. Ler este documento + `api/README.md`
2. Subir stack: `cd api && docker compose up -d` com `USE_MOCK_ORACLE=true`
3. Subir site: `cd site && npm i && npm run dev` (`VITE_API_BASE_URL=http://localhost:8003`)
4. Login bootstrap (`BOOTSTRAP_ADMIN_*`)
5. Testar: Emitir pendentes (mock) → ver status na tabela → Dashboard
6. RabbitMQ UI: `http://localhost:15672` (guest/guest padrão)
7. Antes de Oracle real: Instant Client + `USE_MOCK_ORACLE=false` + DSN válido
8. Antes de PR real: validar payload com `/preview` e homolog

---

## 19. Testes manuais sugeridos

| Cenário | Esperado |
|---------|----------|
| Preview Castelo (mock) | Payload camelCase válido |
| Emitir específica válida | Mensagem na fila + status no painel |
| Material sem de-para | `erro_tipo=sem_depara`, retry → DLQ |
| Sucesso PR | `sent` + tentativa de `dt_integracao` |
| Toggle scheduler off | Auto não roda; emit manual ok |
| Destinatário + report force | E-mail chega / SMTP log |
| Export dashboard | CSV com BOM `;` |
| Nginx `/api/health` | JSON ok; `/` serve SPA |

---

## 20. Referência rápida de portas

| Porta | Serviço |
|------:|---------|
| 5173 | Vite dev (site) |
| 5001 | Nginx (ex.: DDNS atual) |
| 8001 | Extractor |
| 8002 | Processor |
| 8003 | Web API |
| 8004 | Report |
| 5432 | Postgres |
| 5672 / 15672 | RabbitMQ / UI |

---

*Mantenedores: atualizem este documento quando houver mudança de contrato PR, schema Postgres, filas ou fluxo de write-back.*
