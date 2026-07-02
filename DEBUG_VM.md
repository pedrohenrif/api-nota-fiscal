# Guia de debug e operação na VM — Integração NF

Documento de referência para **diagnóstico de falhas**, **consulta de logs** e **reinício de serviços** na VM (homologação e produção).

Complementa:

- [INSTALACAO_VM.md](./INSTALACAO_VM.md) — instalação inicial
- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md) — fluxo operacional e testes

---

## 1. Antes de tudo: checklist rápido

Sempre comece por aqui quando algo não funcionar:

```bash
cd /caminho/para/projeto-nota-fiscal/api

# 1) Todos os containers devem estar Up
docker compose ps

# 2) Health dos serviços HTTP
curl -s http://localhost:8001/health   # extractor
curl -s http://localhost:8002/health   # processor
curl -s http://localhost:8003/health   # web-api (painel)

# 3) Site apontando para a API correta (site/.env)
# VITE_API_BASE_URL=http://IP-DA-VM:8003
```

**Stack completa esperada (5 serviços Docker):**

| Container | Porta | Função |
|-----------|-------|--------|
| `db` | 5432 | Postgres — status das notas |
| `rabbitmq` | 5672 / 15672 | Fila assíncrona |
| `extractor-service` | 8001 | Consulta Oracle + publica na fila |
| `processor-service` | 8002 | De-para + envio ao PR |
| `web-api-service` | 8003 | API do painel (login, emissão, listagem) |

Se `web-api-service` não aparecer no `docker compose ps`, o site **não funciona** mesmo com os outros serviços OK.

---

## 2. Mapa: onde investigar cada problema

Use a coluna **Erro** do painel e o sintoma para saber **qual serviço olhar**:

```text
[Usuario / Browser]
        |
        v
[site :5173]  -----------------> erro de rede/CORS? → site/.env + CORS_ORIGINS
        |
        v
[web-api :8003]  -------------> login/consulta falha? → logs web-api-service
        |
        +--> chama extractor :8001 --> erro Oracle? → logs extractor-service
        |
        v
[RabbitMQ nf.raw]
        |
        v
[processor :8002]  ------------> erro PR HTTP 4xx/5xx? → logs processor-service
        |
        v
[PR] + [Postgres nota_processamento]
```

| Sintoma no painel / site | Serviço provável | Comando de log |
|--------------------------|------------------|----------------|
| Site não abre / tela branca | Frontend (`site/`) | terminal onde roda `npm run dev` |
| `ERR_CONNECTION_REFUSED` :8003 | web-api | `docker compose logs web-api-service --tail 80` |
| Erro ao **Consultar** nota | extractor (+ web-api) | `docker compose logs extractor-service --tail 80` |
| Nota emitida mas não aparece na tabela | processor | `docker compose logs processor-service --tail 80` |
| Coluna **Erro** com `PR HTTP ...` | processor + config PR | logs processor + `.env` PR_* |
| Coluna **Erro** com Oracle / DPY / DPI | extractor | logs extractor + Oracle |
| Status `retry_pending` | processor (retry automático) | aguardar ou ver logs |
| Status `dead_letter` | processor esgotou tentativas | Reemitir no site após corrigir causa |

---

## 3. Comandos essenciais de logs

Todos os comandos assumem que você está em `projeto-nota-fiscal/api`.

### Ver logs em tempo real

```bash
# Todos os serviços
docker compose logs -f

# Um serviço específico
docker compose logs -f extractor-service
docker compose logs -f processor-service
docker compose logs -f web-api-service
```

### Últimas N linhas (mais usado no debug)

```bash
docker compose logs extractor-service --tail 100
docker compose logs processor-service --tail 100
docker compose logs web-api-service --tail 100
docker compose logs rabbitmq --tail 50
docker compose logs db --tail 50
```

### Filtrar por palavra-chave

```bash
docker compose logs processor-service --tail 200 | grep -i "PR HTTP"
docker compose logs processor-service --tail 200 | grep -i "error"
docker compose logs extractor-service --tail 200 | grep -i "oracle\|DPY\|DPI\|ORA-"
```

### Ver se o container caiu ao iniciar

```bash
docker compose ps -a
docker compose logs web-api-service --tail 50
```

Status **Exited** = serviço crashou na subida (erro de código, import, porta em uso, etc.).

---

## 4. Reiniciar serviços

### Reiniciar um serviço (após mudar `.env` ou código montado em volume)

```bash
docker compose restart extractor-service
docker compose restart processor-service
docker compose restart web-api-service
```

### Subir serviço que não está rodando

```bash
docker compose up -d web-api-service
docker compose up -d extractor-service
```

### Recriar container (necessário após mudar volume do Oracle, por exemplo)

```bash
docker compose up -d --force-recreate extractor-service
```

### Rebuild de imagem (após mudar Dockerfile — ex.: libaio)

```bash
docker compose build extractor-service --no-cache
docker compose up -d --force-recreate extractor-service
```

### Subir / parar stack inteira

```bash
docker compose up -d          # sobe tudo
docker compose down           # para tudo (dados Postgres persistem no volume)
docker compose up --build -d  # rebuild + sobe tudo
```

### O que reiniciar após cada tipo de alteração

| Alteração | Reiniciar |
|-----------|-----------|
| `ORACLE_DSN`, `USE_MOCK_ORACLE`, Instant Client | `extractor-service` (rebuild se Dockerfile) |
| `PR_*`, tokens, `PR_ENV` | `processor-service` |
| `JWT_*`, `CORS_ORIGINS`, credenciais admin | `web-api-service` |
| Código Python em `api/services/*` (volume montado) | serviço afetado (`restart`) |
| `site/.env` ou frontend | reiniciar `npm run dev` / rebuild do site |
| `docker-compose.yml` | `docker compose up -d` no serviço alterado |

### Reiniciar o site (frontend)

```bash
cd /caminho/para/projeto-nota-fiscal/site

# Dev
npm run dev -- --host 0.0.0.0

# Se alterou .env do site, pare (Ctrl+C) e suba de novo
```

---

## 5. Debug passo a passo por cenário

### Cenário A — Site não conecta na API

1. `curl http://localhost:8003/health` na VM
2. Se falhar: `docker compose up -d web-api-service` e ver logs
3. Confirme `site/.env`: `VITE_API_BASE_URL=http://IP-DA-VM:8003`
4. Confirme `CORS_ORIGINS` no `api/.env` ou `docker-compose.yml` com a URL do site
5. Reinicie: `docker compose restart web-api-service`

### Cenário B — Consultar nota falha (modal "Emitir nota específica")

1. Logs: `docker compose logs extractor-service --tail 80`
2. Teste Oracle dentro do container:

```bash
docker compose exec extractor-service python -c "
from services.extractor.oracle_client import build_oracle_client
c = build_oracle_client()
print(c.fetch_all('SELECT 1 AS ok FROM dual', {}))
"
```

3. Teste consulta via API (com token de login):

```bash
TOKEN="access_token_do_login"
curl "http://localhost:8003/notas/consultar?estabelecimento=Castelo&nr_sequencia=60809" \
  -H "Authorization: Bearer $TOKEN"
```

4. Erros comuns: Oracle (DPY/DPI/ORA), nota inexistente, operação não liberada (1 ou 39).

### Cenário C — Emitiu no site, nota não aparece / fica parada

1. Verifique se processor está Up: `docker compose ps`
2. Logs: `docker compose logs processor-service --tail 100`
3. RabbitMQ UI: `http://IP-DA-VM:15672` (guest/guest)
   - Fila `nf.raw` — mensagens aguardando processamento
   - Fila `nf.dead` — falhas definitivas
4. Aguarde 10–15 s e clique **Atualizar** no painel

### Cenário D — Nota com erro na coluna Erro (PR HTTP ...)

1. Leia a mensagem completa na coluna **Erro** do painel
2. Logs detalhados: `docker compose logs processor-service --tail 100`
3. Consulte a tabela de erros PR na seção 7 deste documento
4. Corrija `.env` ou dados; reinicie `processor-service`
5. Clique **Reemitir** na linha da nota (status `retry_pending` ou `dead_letter`)

### Cenário E — Atualização de código (git pull)

```bash
cd /caminho/para/projeto-nota-fiscal/api
git pull

# Se mudou Dockerfile
docker compose build
docker compose up -d

# Se mudou só Python/.env
docker compose restart extractor-service processor-service web-api-service
```

---

## 6. Testes manuais úteis (na VM)

### Health

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Login

```bash
curl -s -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SUA_SENHA"}'
```

### Preview de extração (não grava no painel)

```bash
curl "http://localhost:8001/preview?estabelecimento=Castelo"
```

### Teste de autenticação PR (header correto: AccessToken)

```bash
curl -i -X POST "http://prsistemas.ddns.net:6728/PREstAPI/NF" \
  -H "AccessToken: SEU_PR_HOMOLOG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nota":{"nf":"1","serie":"1","fornecedor":{"cnpj":"00000000000000"},"dataNF":"2026-03-05T00:00:00Z","operador":"TESTE","valorTotal":0,"qtdItens":0,"produtos":[]}}'
```

- **401** → token inválido
- **400** → token OK, payload inválido (esperado em teste mínimo)
- **200** → sucesso

### Consultar status no Postgres

```bash
docker compose exec db psql -U tasy -d tasy_db -c \
  "SELECT id, nf, nr_sequencia, estabelecimento, status, tentativas, left(erro, 120) AS erro FROM nota_processamento ORDER BY id DESC LIMIT 10;"
```

---

## 7. Erros frequentes e como interpretar

### Painel / Web API

| Mensagem / sintoma | Causa | Ação |
|--------------------|-------|------|
| `ERR_CONNECTION_REFUSED` :8003 | web-api parado | `docker compose up -d web-api-service` |
| `Credenciais invalidas` | login/senha errados | `.env` BOOTSTRAP_ADMIN_* ou usuário criado |
| Erro CORS no browser | origem não permitida | ajustar `CORS_ORIGINS`, restart web-api |
| `Servico de extracao indisponivel` | extractor down ou Oracle falhou | logs extractor-service |

### Oracle / Extractor

| Mensagem | Causa | Ação |
|----------|-------|------|
| `DPY-3001` / thick mode | Instant Client ausente no container | montar `/opt/oracle/instantclient_*` no compose |
| `DPI-1047` / `libaio.so.1` | falta libaio na imagem | `docker compose build extractor-service --no-cache` |
| `ORA-01017` | usuário/senha Oracle | corrigir `ORACLE_DSN` |
| timeout / TNS | rede, porta, service_name | validar IP, porta **10521**, firewall |
| Nota não elegível | operação ≠ 1 ou 39 | consultar no modal antes de emitir |

### PR / Processor

| Mensagem | Causa | Ação |
|----------|-------|------|
| `De-para vazio` / `codProd=` | material Tasy sem vínculo no PR | Swagger: GET `/Controle/produtos/{codMaterial}` |
| `PR HTTP 401` / acesso negado | token ou header errado | PR usa header **`AccessToken`**, não Bearer; validar `PR_HOMOLOG_TOKEN` |
| `The nota field is required` | payload sem wrapper `{nota:...}` | atualizar código (processor); reemitir |
| `dataNF ... DateTime` | data em formato errado | datas devem ser ISO `2026-03-05T00:00:00Z` |
| `PR HTTP 404` | URL base errada | `PR_BASE_URL_*` **sem** `/NF` no final |
| de-para / produto | material Tasy sem vínculo no PR | conferir GET `/Controle/produtos/{cod}` no Swagger PR |
| `retry_pending` | falha temporária, retry automático | corrigir causa e aguardar ou reemitir |
| `dead_letter` | 3 tentativas esgotadas | corrigir causa → **Reemitir** no site |

### Status no painel

| Status | Significado |
|--------|-------------|
| `sent` | Enviado ao PR com sucesso |
| `retry_pending` | Falhou; processor tentará de novo (até 3x, intervalo ~10 s) |
| `dead_letter` | Esgotou tentativas; mensagem pode estar em `nf.dead` no RabbitMQ |

---

## 8. RabbitMQ — inspeção visual

URL: `http://IP-DA-VM:15672`  
Credenciais padrão: `guest` / `guest`

| Fila | Significado |
|------|-------------|
| `nf.raw` | Notas aguardando ou em retry |
| `nf.dead` | Notas com falha definitiva |

Se `nf.raw` acumula mensagens e processor está Up, veja logs do processor.  
Se `nf.dead` tem mensagens, corrija o erro raiz e use **Reemitir** no painel.

---

## 9. Variáveis críticas do `.env` (api/)

Referência rápida — **nunca commitar** o `.env` com senhas reais.

```env
# Oracle
USE_MOCK_ORACLE=false
ORACLE_DSN=oracle+cx_oracle://usuario:senha@host:10521/?service_name=...
ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient_21_19

# Extração manual (recomendado em homolog)
EXTRACTION_SCHEDULER_ENABLED=false

# PR
PR_ENV=homolog                    # ou production
PR_BASE_URL_HOMOLOG=http://.../PREstAPI    # SEM /NF no final
PR_HOMOLOG_TOKEN=...

# Painel
JWT_SECRET=...
CORS_ORIGINS=http://IP-DA-VM:5173
EXTRACTOR_URL=http://localhost:8001   # override no compose: extractor-service:8001
```

---

## 10. Fluxo de handoff para produção

Checklist para quem assumir a operação:

- [ ] Caminho do projeto na VM documentado
- [ ] `docker compose ps` com 5 serviços Up
- [ ] `curl` health 8001/8002/8003 OK
- [ ] Teste Oracle (`SELECT 1 FROM dual`) OK
- [ ] Site acessível e login funcionando
- [ ] `PR_ENV` correto (homolog vs production)
- [ ] Tokens PR validados no Swagger
- [ ] Senha admin alterada (`BOOTSTRAP_ADMIN_*`)
- [ ] `JWT_SECRET` forte em produção
- [ ] IP da VM na whitelist do PR (se exigido)
- [ ] Este documento + [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md) acessíveis à equipe

### Contatos / escalonamento (preencher na implantação)

| Área | Responsável | Observação |
|------|-------------|------------|
| VM / Docker | | |
| Oracle Tasy | | |
| PR Sistemas | | |
| Painel / integração | | |

---

## 11. Referência rápida — cola de comandos

```bash
cd /caminho/para/projeto-nota-fiscal/api

# Status
docker compose ps
docker compose ps -a

# Health
curl -s http://localhost:8001/health && echo
curl -s http://localhost:8002/health && echo
curl -s http://localhost:8003/health && echo

# Logs
docker compose logs -f processor-service
docker compose logs extractor-service --tail 100
docker compose logs web-api-service --tail 100

# Restart
docker compose restart processor-service
docker compose restart extractor-service
docker compose restart web-api-service
docker compose up -d web-api-service

# Oracle
docker compose exec extractor-service ls -la /opt/oracle/instantclient_21_19
docker compose exec extractor-service python -c "from services.extractor.oracle_client import build_oracle_client; c=build_oracle_client(); print(c.fetch_all('SELECT 1 AS ok FROM dual', {}))"

# Postgres — últimas notas
docker compose exec db psql -U tasy -d tasy_db -c "SELECT nf, status, tentativas, left(erro,80) FROM nota_processamento ORDER BY id DESC LIMIT 5;"
```

---

## 12. Documentação relacionada

- [INSTALACAO_VM.md](./INSTALACAO_VM.md)
- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md)
- [api/README.md](./api/README.md)
