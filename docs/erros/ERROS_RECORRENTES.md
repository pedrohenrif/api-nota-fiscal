# Erros recorrentes e plantão — Integração NF (Tasy → PR)

Documento para **outro desenvolvedor** intervir com o time de férias.  
Foco nos problemas que **já aconteceram** e na ação correta.

Complementa: [DEBUG_VM.md](./DEBUG_VM.md) · [DEBUG_PR_SQLSERVER.md](./DEBUG_PR_SQLSERVER.md) · [DOCUMENTACAO_TECNICA.md](../dev/DOCUMENTACAO_TECNICA.md)

---

## 1. Checklist rápido (sempre)

```bash
cd ~/GHR_Tech/01_Testes/api-nota-fiscal/api   # ajuste o path da VM

docker compose ps
curl -s http://localhost:8001/health   # extractor
curl -s http://localhost:8002/health   # processor
curl -s http://localhost:8003/health   # web-api
curl -s http://localhost:8004/health   # report

docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```

| Sintoma | Onde olhar |
|---------|------------|
| Fila `nf.raw` milhares | PR lento / timeout + scheduler ainda publicando |
| Consumer parado | `docker compose logs processor-service --tail 100` |
| Site login / CORS | `web-api` + `CORS_ORIGINS` + rebuild do `site` |
| E-mail não chega | `report-service` + SMTP + destinatários **ativos** |
| Nota “sent” mas Tasy sem `dt_integracao` | write-back Oracle (UPDATE) |

Painel (perfil **dev**): Dashboard → bloco **Filas e processor**.

---

## 2. Erros mais recorrentes

### 2.1 `Execution Timeout Expired` (PR HTTP 400)

**O que é:** o POST chega no PR, mas o **SQL Server do PR** estoura timeout (~30s).  
**Não é** falha de JSON nosso nem timeout do `httpx` (90s).

**Log típico (com `PR_DEBUG_HTTP=true`):**
```text
[PR DEBUG] POST resposta ... status=400 elapsed_ms≈31000
erro=PR HTTP 400: Execution Timeout Expired...
```

**O que fazer:**
1. Não encher a fila — desligar scheduler das unidades ou aguardar backpressure (`QUEUE_BACKPRESSURE_MAX`).
2. Avisar o time do **PR** (banco lento / lock).
3. Após estabilizar: emitir **1 nota específica** de teste.
4. Se `nf.raw` estiver absurdo: purgar (ver §3).

**Código:** `processor/dispatcher.py`, circuit breaker trata esse texto como timeout.

---

### 2.2 Fila RabbitMQ explode (`nf.raw` dezenas de milhares)

**Causas já vistas:**
- PR em timeout + extractor/scheduler continua publicando
- Antigo bug: circuit aberto **republicava** mensagens (corrigido — agora pausa)
- Dead letter publicado no Rabbit (`nf.dead`) acumulando lixo antigo

**O que fazer agora:**
```bash
# Parar injeção
# Painel Configurações: desligar scheduler das unidades
# OU api/.env: EXTRACTION_SCHEDULER_ENABLED=false
docker compose restart extractor-service

# Alívio (só se backlog for lixo / irrecuperável)
docker compose exec rabbitmq rabbitmqctl purge_queue nf.raw
docker compose exec rabbitmq rabbitmqctl purge_queue nf.dead
docker compose restart processor-service
```

**Proteções no código:**
- Circuit breaker + pausa do consumer
- Scheduler não publica se `nf.raw >= QUEUE_BACKPRESSURE_MAX` (default 200)
- Retry de timeout limitado a **2 dias** (`MAX_RETRY_AGE_DAYS`)
- `PUBLISH_DEAD_LETTER_QUEUE=false` → dead letter só no Postgres

---

### 2.3 Alerta “Processor sem atividade / possível travamento”

**Com `nf.raw = 0` e Consumer = Rodando:** em geral é **idle normal** (nada para processar), não travamento.

Stall verdadeiro = **há mensagens em `nf.raw`** e zero atividade por ~3 min.

(Corrigido no health/ops: não alarma com fila vazia.)

---

### 2.4 `sem_depara`

Material Tasy sem vínculo no PR.

1. Cadastrar de-para no **ambiente/unidade corretos** (homolog × produção; token da unidade).
2. No painel: **Reemitir**.

---

### 2.5 `sem_lote`

Item exige lote e não veio no Tasy.

1. Corrigir lote no Tasy.  
2. **Reemitir**.

---

### 2.6 `retorno_pr` — “Já existe NF + FORNECEDOR”

Tratado como **sucesso** (`jaExistiaNoPR`): grava `sent` + tenta write-back Tasy.  
Não reemitir em loop.

---

### 2.7 Nota emitida (verde) mas não aparece na lista

1. Aplicar filtros no painel (lista não carrega sozinha).
2. Conferir Postgres:
```bash
docker compose exec db psql -U tasy -d tasy_db -c \
  "SELECT nf, nr_sequencia, status, left(erro,80) FROM nota_processamento ORDER BY id DESC LIMIT 10;"
```
3. Se sumiu na fila e não processou: fila/processor (acima).

---

### 2.8 DATA NF “errada” na lista (−1 dia)

Origem: `tasy.nota_fiscal.dt_emissao` → `dataNF` → Postgres `data_nf`.  
Bug de UI: `T00:00:00Z` + `toLocaleDateString` no Brasil virava dia anterior.  
**Corrigido** em `site/src/lib/format.ts` (data de calendário). Rebuild do site se ainda aparecer antigo.

---

### 2.9 Extração Oracle / Instant Client

| Erro | Ação |
|------|------|
| `ORA-12170` / timeout | Rede/firewall até o Oracle |
| `DPI-1047` / `libaio` | Rebuild imagem extractor com Instant Client + libaio |
| Extractor “indisponível” | `docker compose ps` + logs `extractor-service` |

---

### 2.10 E-mail / destinatários

- Destinatário **inativo** não recebe (não há exclusão — só inativar).
- SMTP: `SMTP_*` no `.env` do report.
- Reset de senha do painel usa o **mesmo SMTP**.

---

## 3. Retry (comportamento atual)

| Tipo de erro | Comportamento |
|--------------|---------------|
| Negócio (`sem_depara`, `retorno_pr`, …) | Até `MAX_PROCESSING_RETRIES` (3), depois `dead_letter` |
| Timeout / PR lento / circuit | Pode retentar até **`MAX_RETRY_AGE_DAYS=2`**, depois `dead_letter` |
| Após `dead_letter` | Só **Reemitir** manual no painel |

Env relevantes (`api/.env`):

```env
MAX_PROCESSING_RETRIES=3
MAX_RETRY_AGE_DAYS=2
PUBLISH_DEAD_LETTER_QUEUE=false
QUEUE_BACKPRESSURE_MAX=200
PR_HTTP_TIMEOUT_SECONDS=90
PR_CIRCUIT_FAILURE_THRESHOLD=5
PR_CIRCUIT_OPEN_SECONDS=120
PR_DEBUG_HTTP=false
```

Debug POST ao PR (ligar só para diagnóstico):

```env
PR_DEBUG_HTTP=true
```
```bash
docker compose up -d --force-recreate processor-service
docker compose logs -f processor-service | grep --line-buffered "PR DEBUG"
```
Desligar depois: `PR_DEBUG_HTTP=false` + recreate.

---

## 4. Papéis do painel (não confundir)

| Papel | Uso |
|-------|-----|
| `adm` | Global: config, usuários, todas unidades |
| `adm_local` | Usuários/destinatários/logs da **própria** unidade |
| `usuario` | Operação da unidade |
| `dev` | Como adm operacional + **Auditoria** + **filas**; sem Configurações |

---

## 5. Comandos de emergência (copiar/colar)

```bash
cd ~/GHR_Tech/01_Testes/api-nota-fiscal
git pull
cd api

docker compose up -d --force-recreate processor-service extractor-service web-api-service report-service

docker compose exec rabbitmq rabbitmqctl list_queues name messages consumers
docker compose exec rabbitmq rabbitmqctl purge_queue nf.raw
docker compose exec rabbitmq rabbitmqctl purge_queue nf.dead

docker compose logs processor-service --tail 80
docker compose logs extractor-service --tail 80
```

Frontend (após mudança no `site/`):

```bash
cd ../site
npm install
npm run build
# nginx: sudo nginx -t && sudo systemctl reload nginx
```

---

## 6. Contatos / decisão

1. Fila e processor saudáveis?  
2. PR respondendo (1 nota específica + log)?  
3. De-para / lote / valor no Tasy e PR?  
4. Só então reemitir em massa ou religar scheduler.
