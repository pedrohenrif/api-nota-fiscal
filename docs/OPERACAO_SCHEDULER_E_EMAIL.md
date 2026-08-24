# Operação — Scheduler por estabelecimento e relatório por e-mail

Este documento explica como **ligar/desligar** a extracao automatica e o envio de e-mails, pelo **`.env`** e pelo **site** (admin).

Complementa:

- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md)
- [DEBUG_VM.md](./DEBUG_VM.md)

---

## Visao geral

| Controle | O que faz | Intervalo | Onde liga/desliga |
|----------|-----------|-----------|-------------------|
| **Master extractor** | Liga/desliga o ciclo automatico **global** | 6 min (`POLL_INTERVAL_MINUTES`) | `api/.env` → `EXTRACTION_SCHEDULER_ENABLED` |
| **Scheduler por unidade** | Quais estabelecimentos entram no ciclo automatico | 6 min | Site → **Configuracoes** (ou Postgres) |
| **Master e-mail** | Liga/desliga o loop automatico de relatorios | 30 min (`REPORT_INTERVAL_MINUTES`) | `api/.env` → `REPORT_SCHEDULER_ENABLED` |
| **Relatorio por unidade** | Quais estabelecimentos recebem e-mail automatico | 30 min | Site → **Configuracoes** |
| **Destinatarios** | Para quem o e-mail vai | — | `api/.env` → `REPORT_EMAIL_*` |

```text
EXTRACTION_SCHEDULER_ENABLED=true   (master no .env)
        +
scheduler_enabled=true na unidade  (site Configuracoes)
        =
extractor busca pendentes daquela unidade a cada 6 min

REPORT_SCHEDULER_ENABLED=true       (master no .env)
        +
report_enabled=true na unidade     (site Configuracoes)
        +
REPORT_EMAIL_CASTELO=...           (destinatarios no .env)
        =
report-service envia e-mail a cada 30 min
```

**Importante:** emissao **manual** pelo painel (“Emitir pendentes” / “Emitir nota especifica”) **nao depende** dos toggles de scheduler. Continua funcionando mesmo com scheduler desligado.

---

## 1. Parar / ligar o extractor automatico

### 1.1 Parar **tudo** (todas as unidades) — via `.env`

No arquivo `api/.env`:

```env
EXTRACTION_SCHEDULER_ENABLED=false
```

Reinicie o extractor:

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose restart extractor-service
```

Conferir:

```bash
curl -s http://localhost:8001/health
```

Esperado: `"scheduler_enabled": false` e `"scheduler_running": false`.

Para religar o master:

```env
EXTRACTION_SCHEDULER_ENABLED=true
POLL_INTERVAL_MINUTES=6
```

```bash
docker compose restart extractor-service
```

### 1.2 Parar / ligar **por estabelecimento** — via site (recomendado)

1. Login como **admin**
2. Menu **Configuracoes**
3. Na coluna **Scheduler (6 min)**, desmarque a unidade (ex.: Castelo) para **parar** so aquela
4. Marque novamente para **ligar** so aquela

Nao precisa reiniciar Docker — a mudanca vale no **proximo ciclo** do extractor.

Exemplos:

| Castelo | HRAS | HRT | Ponta Pora | Efeito no ciclo automatico |
|---------|------|-----|------------|----------------------------|
| Off | Off | Off | Off | Master pode estar `true`, mas **ninguem** e processado |
| On | Off | Off | Off | So Castelo a cada 6 min |
| On | On | On | On | As 4 unidades |

### 1.3 Conferir quais unidades estao ativas no scheduler

```bash
curl -s http://localhost:8001/health
```

Campo util: `scheduler_estabelecimentos` — lista so as unidades com `scheduler_enabled=true`.

---

## 2. Parar / ligar o envio de e-mail

### 2.1 Parar **todos** os e-mails automaticos — via `.env`

No `api/.env`:

```env
REPORT_SCHEDULER_ENABLED=false
```

Reinicie o report-service:

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose restart report-service
```

Conferir:

```bash
curl -s http://localhost:8004/health
```

Esperado: `"scheduler_enabled": false`.

Para religar:

```env
REPORT_SCHEDULER_ENABLED=true
REPORT_INTERVAL_MINUTES=30
```

```bash
docker compose restart report-service
```

### 2.2 Parar / ligar e-mail **por estabelecimento** — via site

1. Login como **admin**
2. Menu **Configuracoes**
3. Coluna **Relatorio e-mail (30 min)** — desmarque para parar aquela unidade; marque para ligar

Tambem e necessario ter destinatarios no `.env` (senao o servico registra “Sem destinatarios” e nao envia):

```env
REPORT_EMAIL_CASTELO=estoque.castelo@empresa.com
REPORT_EMAIL_HRAS=estoque.hras@empresa.com
REPORT_EMAIL_HRT=estoque.hrt@empresa.com
REPORT_EMAIL_PONTA_PORA=estoque.pp@empresa.com
```

Varios e-mails na mesma unidade: separe por virgula.

Apos alterar destinatarios ou SMTP no `.env`:

```bash
docker compose restart report-service
```

### 2.3 Disparo manual (nao depende do toggle automatico)

No site → **Configuracoes** → botao **Enviar relatorio agora** em cada linha.

Isso chama o `report-service` imediatamente (util para teste). O toggle `report_enabled` controla so o **ciclo automatico** de 30 min; o botao manual pode ser usado mesmo com o automatico desligado.

### 2.4 Conta SMTP

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=GHR@ghr.com.br
SMTP_PASSWORD=xxxx xxxx xxxx xxxx   # app password Gmail
SMTP_FROM_NAME=API GHR
SMTP_USER_FALLBACK=api@ghr.com.br
SMTP_PASSWORD_FALLBACK=xxxx xxxx xxxx xxxx
```

Se a conta principal falhar na autenticacao, o servico tenta a de contingencia uma vez.

**Nunca commitar senhas** no Git — apenas no `.env` da VM.

---

## 3. O que o e-mail contem

Relatorio HTML por estabelecimento, com secoes (vazias sao omitidas):

1. **Notas integradas** — `status=sent` no periodo (`REPORT_LOOKBACK_MINUTES`); **enviada uma unica vez** (tabela `nota_report_envio`)
2. **Notas nao integradas** — elegiveis no Tasy sem bloqueio de de-para/lote; **enviada uma unica vez**
3. **Sem de-para** — itens sem vinculo no PR; **pode repetir** a cada ciclo ate resolver
4. **Sem lote** — itens sem lote; **pode repetir** a cada ciclo ate resolver
5. **Erros PR** — `dead_letter` / `retry_pending` recentes; **enviado uma unica vez** por nota/categoria

A mesma nota nao entra em mais de uma secao Oracle (prioridade: sem de-para > sem lote > nao integrada).

No modo automatico, se nao houver nenhuma ocorrencia nova, **o e-mail nao e enviado**.

---

## 4. Servicos Docker envolvidos

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose up -d
docker compose ps
```

| Servico | Porta | Papel |
|---------|-------|-------|
| `extractor-service` | 8001 | Ciclo 6 min (respeita scheduler por unidade) |
| `processor-service` | 8002 | Consome fila e envia ao PR |
| `web-api-service` | 8003 | Painel + APIs admin |
| `report-service` | 8004 | Ciclo 30 min + disparo manual de e-mail |
| `db` / `rabbitmq` | 5432 / 5672 | Infra |

Health:

```bash
curl -s http://localhost:8001/health   # extractor
curl -s http://localhost:8004/health   # report
curl -s http://localhost:8003/health   # web-api
```

---

## 5. Checklist rapido

### Quero so Castelo no automatico (extracao)

1. `.env`: `EXTRACTION_SCHEDULER_ENABLED=true`
2. Site Configuracoes: so **Castelo** com Scheduler ligado
3. `docker compose restart extractor-service` (se alterou o `.env`)

### Quero parar e-mails de todas as unidades

1. `.env`: `REPORT_SCHEDULER_ENABLED=false`
2. `docker compose restart report-service`

### Quero parar so o e-mail do HRAS (manter as outras)

1. Site Configuracoes: desligar **Relatorio e-mail** do HRAS  
   (sem mexer no `.env`)

### Quero testar o e-mail agora

1. Preencher `REPORT_EMAIL_*` e SMTP no `.env`
2. `docker compose restart report-service`
3. Site Configuracoes → **Enviar relatorio agora**
