# Operação e testes — Integração NF (Instituto Mais Saúde)

Documento técnico para operação diária, testes em homologação e alterações futuras na VM.

Complementa o guia de instalação: [INSTALACAO_VM.md](./INSTALACAO_VM.md).

---

## 1. Visão geral do fluxo

```text
[Tasy Oracle Homolog]
        |
        |  (1) EXTRACAO — manual pelo site OU scheduler automatico
        v
[extractor-service :8001]
        |  publica JSON da nota
        v
[RabbitMQ — fila nf.raw]
        |
        |  (2) PROCESSAMENTO — automatico, sempre ligado
        v
[processor-service :8002]
        |  de-para produto (GET /Controle/produtos/{codVinculo})
        |  grava NF (POST /NF)
        v
[PR Homolog / Producao]
        |
        |  status gravado em
        v
[PostgreSQL — nota_processamento]
        |
        |  (3) VISUALIZACAO
        v
[web-api :8003] → [site :5173]
```

### O que é manual vs automatico

| Etapa | Modo atual recomendado (homolog) | Como funciona |
|-------|----------------------------------|---------------|
| Oracle → fila | **Manual** (site) | Botoes "Emitir pendentes" ou "Emitir nota especifica" |
| Fila → PR | **Automatico** | Processor consome `nf.raw` ao subir o Docker |
| Status no painel | **Consulta** | Tabela "Notas recentes" apos processamento |

---

## 2. Modo de operacao: disparo manual pelo site

### Configuracao no `api/.env`

```env
EXTRACTION_SCHEDULER_ENABLED=false
EXTRACTION_RUN_ON_STARTUP=false
USE_MOCK_ORACLE=false          # VM homolog: Oracle real
ORACLE_DSN=oracle+cx_oracle://usuario:senha@host:10521/?service_name=nome_do_service
PR_ENV=homolog
```

**Formato do `ORACLE_DSN`:** aceita URL estilo SQLAlchemy (como acima) ou string nativa Oracle. O ping no IP do banco **nao garante** conexao — o extractor usa porta **10521** e `service_name` da URL.

O Tasy homolog exige **modo thick**. O Instant Client fica na VM (ex.: `/opt/oracle/instantclient_21_19`) e e montado no container via `docker-compose.yml`. No `api/.env`:

```env
ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_19
```

```bash
docker compose up -d extractor-service
docker compose exec extractor-service ls -la /opt/oracle/instantclient_21_19
```

Teste a conexao:

```bash
docker compose exec extractor-service python -c "
from services.extractor.oracle_client import build_oracle_client
c = build_oracle_client()
print(c.fetch_all('SELECT 1 AS ok FROM dual', {}))
"
```

Esperado: `[{'OK': 1}]`.

| Variavel | Valor manual | Efeito |
|----------|--------------|--------|
| `EXTRACTION_SCHEDULER_ENABLED` | `false` | **Nao** roda ciclo a cada 6 min |
| `EXTRACTION_RUN_ON_STARTUP` | `false` | **Nao** extrai ao subir o container |
| `USE_MOCK_ORACLE` | `false` | Consulta o Tasy real (homolog) |

### Quando ativar modo automatico (futuro)

```env
EXTRACTION_SCHEDULER_ENABLED=true
POLL_INTERVAL_MINUTES=6
EXTRACTION_RUN_ON_STARTUP=false   # ou true para rodar ao subir
```

Com scheduler ligado, o extractor busca pendentes dos **4 estabelecimentos** a cada intervalo, sem acao no site.

Apos alterar o `.env`:

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose restart extractor-service
```

---

## 3. Codigos de estabelecimento (Tasy)

Definidos em `api/services/extractor/extraction_profiles.py`:

| Nome no site | `cd_estabelecimento` Tasy |
|--------------|---------------------------|
| Castelo | 8 |
| HRAS | 9 |
| HRT (Itaituba) | 7 |
| Ponta Pora | 16 |

### Filtros SQL usados na extracao (cabecalho)

```sql
WHERE ie_tipo_nota = 'EN'
  AND dt_integracao IS NULL
  AND cd_estabelecimento = :cd_estabelecimento
  AND ie_situacao NOT IN (2, 3)
  AND cd_operacao_nf IN (1, 39)
  AND TRUNC(dt_emissao) >= DATE '2024-05-14'
  AND TRUNC(dt_atualizacao_estoque) >= DATE '2025-09-21'
```

Emissao por **nota especifica** valida operacao, estabelecimento e demais regras antes de publicar na fila.

---

## 4. Comandos para iniciar na VM

Substitua `/caminho/para/projeto-nota-fiscal` pelo caminho real.

### 4.1 Backend (APIs + infra)

```bash
cd /caminho/para/projeto-nota-fiscal/api

# Primeira vez ou apos mudanca de codigo/.env
docker compose up --build -d

# Subir sem rebuild (dia a dia)
docker compose up -d

# Ver status
docker compose ps

# Ver logs
docker compose logs -f
docker compose logs -f extractor-service
docker compose logs -f processor-service
docker compose logs -f web-api-service
```

### 4.2 Health checks

```bash
curl http://localhost:8001/health   # extractor
curl http://localhost:8002/health   # processor (consumer_running: true)
curl http://localhost:8003/health   # web-api
```

Resposta esperada do extractor em modo manual:

```json
{
  "scheduler_enabled": false,
  "scheduler_running": false,
  "poll_interval_minutes": 6
}
```

### 4.3 Site (frontend)

**Desenvolvimento / testes na VM:**

```bash
cd /caminho/para/projeto-nota-fiscal/site

npm install          # primeira vez
cp .env.example .env # primeira vez — ajuste VITE_API_BASE_URL

# Editar site/.env:
# VITE_API_BASE_URL=http://IP-DA-VM:8003

npm run dev -- --host 0.0.0.0
```

Acesso: `http://IP-DA-VM:5173`

**Producao (build estatico):**

```bash
cd /caminho/para/projeto-nota-fiscal/site
npm run build
npx serve -s dist -l 5173
# ou publicar site/dist/ via Nginx
```

### 4.4 CORS (obrigatorio se site nao for localhost)

No `api/docker-compose.yml`, servico `web-api-service`:

```yaml
environment:
  CORS_ORIGINS: http://IP-DA-VM:5173,http://localhost:5173
```

Ou via `api/.env`:

```env
CORS_ORIGINS=http://IP-DA-VM:5173
```

Reiniciar:

```bash
docker compose up -d web-api-service
```

### 4.5 Parar tudo

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose down
```

---

## 5. Operacao pelo site

Login inicial: `admin` / `admin123` (altere em `BOOTSTRAP_ADMIN_*` no `.env`).

### 5.1 Emitir pendentes

- Seleciona o **estabelecimento**
- Clica **Emitir pendentes**
- O extractor consulta o Tasy (filtros acima) e publica cada nota na fila `nf.raw`
- O processor processa **automaticamente** em segundos

### 5.2 Emitir nota especifica

- Modal **Emitir nota especifica**
- Informa **NR Sequencia** → **Consultar**
- Sistema valida operacao liberada (`1` ou `39`)
- **Confirmar emissao** publica so aquela nota na fila

### 5.3 Reemitir

- Na tabela **Notas recentes**, linhas com status `retry_pending` ou `dead_letter`
- Botao **Reemitir** rebusca no Tasy e republica na fila

### 5.4 Filtros

Filtra por NF, NR Sequencia, fornecedor, status, datas — consulta o Postgres (historico de processamento).

---

## 6. O que o site mostra (e o que nao mostra)

### Mostra

- Notas que **ja entraram** no fluxo (processor gravou em `nota_processamento`)
- Status: `sent`, `retry_pending`, `dead_letter`
- Tentativas e **mensagem de erro do PR**
- NF, NR Sequencia, fornecedor, data NF

### Nao mostra

- Notas que ainda estao **somente no Tasy** (nunca emitidas)
- Conteudo da fila RabbitMQ antes do processor
- Preview em massa do Oracle (use endpoint `/preview` no extractor para debug)

### Ver a fila RabbitMQ

Interface web: `http://IP-DA-VM:15672` (usuario/senha padrao: `guest` / `guest`)

Filas: `nf.raw` (pendentes), `nf.dead` (falha definitiva apos retries).

---

## 7. Roteiro de teste em homolog

### Checklist antes do teste

- [ ] `USE_MOCK_ORACLE=false` no `api/.env`
- [ ] `ORACLE_DSN` correto para homolog
- [ ] `EXTRACTION_SCHEDULER_ENABLED=false`
- [ ] `PR_ENV=homolog`
- [ ] Docker: todos os containers `Up` (`docker compose ps`)
- [ ] `curl http://localhost:8003/health` OK
- [ ] Site com `VITE_API_BASE_URL` apontando para `:8003`
- [ ] CORS com IP/porta do site

### Teste 1 — Health

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Teste 2 — Login

```bash
curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Teste 3 — Consultar nota no Tasy (via API)

```bash
TOKEN="cole_o_access_token_aqui"

curl "http://localhost:8003/notas/consultar?estabelecimento=Castelo&nr_sequencia=SEU_NR_SEQUENCIA" \
  -H "Authorization: Bearer $TOKEN"
```

Esperado: `valido: true` se operacao e estabelecimento OK.

### Teste 4 — Emitir pelo site

1. Emitir nota especifica ou pendentes (Castelo)
2. Aguardar 5–15 s
3. **Atualizar** tabela no site
4. Verificar status e coluna Erro

### Teste 5 — Preview direto no extractor (debug)

```bash
curl "http://localhost:8001/preview?estabelecimento=Castelo"
```

Lista payloads que seriam publicados na fila (nao grava status no painel).

---

## 8. Status e erros

| Status | Significado |
|--------|-------------|
| `sent` | Enviado ao PR com sucesso |
| `retry_pending` | Falhou; processor tentara de novo (ate 3x) |
| `dead_letter` | Esgotou tentativas; usar **Reemitir** no site |

Erros do PR aparecem na coluna **Erro** (HTTP 4xx/5xx ou mensagem de negocio no corpo da resposta).

---

## 9. Portas e servicos

| Servico | Porta | URL exemplo |
|---------|-------|-------------|
| Extractor | 8001 | `http://IP:8001/health` |
| Processor | 8002 | `http://IP:8002/health` |
| Web API | 8003 | `http://IP:8003/auth/login` |
| Site (dev) | 5173 | `http://IP:5173` |
| RabbitMQ UI | 15672 | `http://IP:15672` |
| Postgres | 5432 | interno / ops |

---

## 10. Alteracoes comuns

| Objetivo | Onde alterar | Reiniciar |
|----------|--------------|-----------|
| Desligar/ligar scheduler | `api/.env` → `EXTRACTION_SCHEDULER_ENABLED` | `docker compose restart extractor-service` |
| Oracle homolog | `api/.env` → `ORACLE_DSN`, `USE_MOCK_ORACLE=false` | `docker compose restart extractor-service` |
| PR homolog/producao | `api/.env` → `PR_ENV`, tokens | `docker compose restart processor-service` |
| Codigo estabelecimento | `api/services/extractor/extraction_profiles.py` | rebuild extractor |
| Senha admin | `api/.env` → `BOOTSTRAP_ADMIN_*` | `docker compose restart web-api-service` |
| URL API no site | `site/.env` → `VITE_API_BASE_URL` | reiniciar `npm run dev` |

---

## 11. Troubleshooting rapido

| Sintoma | Causa provavel | Acao |
|---------|----------------|------|
| Site: `ERR_CONNECTION_REFUSED` :8003 | web-api parado | `docker compose ps` → `docker compose up -d web-api-service` |
| Lista vazia no site | Nenhuma nota emitida ainda | Emitir pelo site; aguardar processor |
| `retry_pending` / erro PR | PR rejeitou ou rede | Ver coluna Erro; testar na VM (IP fixo) |
| Nota nao elegivel | Operacao diferente de 1/39 | Consultar no modal antes de emitir |
| Scheduler rodando sozinho | `EXTRACTION_SCHEDULER_ENABLED=true` | Colocar `false` e reiniciar extractor |
| Mock em vez de Oracle | `USE_MOCK_ORACLE=true` | Colocar `false` na VM |
| `DPY-3001` / thick mode | Instant Client nao montado no container | Montar `/opt/oracle/instantclient_21_19` no compose; `docker compose up -d extractor-service` |
| `DPI-1047` / `libaio.so.1` | Falta libaio no container | `docker compose build extractor-service --no-cache && docker compose up -d --force-recreate extractor-service` |

---

## 12. Documentacao relacionada

- [INSTALACAO_VM.md](./INSTALACAO_VM.md) — instalacao inicial na VM
- [api/README.md](./api/README.md) — arquitetura e endpoints
- [site/README.md](./site/README.md) — frontend
- [api/Documentos_Projeto/README_TASY_PR.md](./api/Documentos_Projeto/README_TASY_PR.md) — contexto Tasy → PR
