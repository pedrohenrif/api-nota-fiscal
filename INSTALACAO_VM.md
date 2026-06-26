# Instalação na VM — Integração NF (Instituto Mais Saúde)

Guia de instalação e execução do projeto em servidor (VM Ubuntu/Linux).

## Estrutura do projeto

```text
projeto-nota-fiscal/
  api/          # Backend (microserviços + Docker Compose)
  site/         # Frontend (React + Vite)
```


| Pasta   | Conteúdo                                          |
| ------- | ------------------------------------------------- |
| `api/`  | Extractor, Processor, Web API, Postgres, RabbitMQ |
| `site/` | Painel web de emissão e acompanhamento            |


---

## 1. Pré-requisitos na VM

```bash
# Docker + Compose
sudo apt update
sudo apt install -y docker.io docker-compose-plugin

# Node.js 18+ (para o frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar instalação
docker --version
docker compose version
node -v
npm -v
```

Adicionar o usuário ao grupo docker (se necessário):

```bash
sudo usermod -aG docker $USER
newgrp docker
# Faça logout e login novamente para aplicar
```

---

## 2. Backend (`api/`)

### 2.1 Entrar na pasta e configurar ambiente

Substitua `/caminho/para/projeto-nota-fiscal` pelo caminho real na VM.

```bash
cd /caminho/para/projeto-nota-fiscal/api

cp .env.example .env
nano .env
```

### 2.2 Variáveis importantes no `.env`

```env
# Oracle Tasy (obrigatório em produção na VM)
USE_MOCK_ORACLE=false
ORACLE_DSN=oracle+cx_oracle://usuario:senha@host-oracle:1521/?service_name=TASY

# PR — homologação (padrão) ou produção
PR_ENV=homolog

# Segurança do painel
JWT_SECRET=troque-por-uma-chave-segura
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=troque-a-senha-inicial
```

> **Homologação:** `PR_ENV=homolog` usa token único e URL de homolog.  
> **Produção:** altere para `PR_ENV=production` e configure os tokens por estabelecimento no `.env`.

### 2.3 Subir a stack com Docker

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose up --build -d
```

### 2.4 Verificar se os serviços subiram

```bash
docker compose ps

curl http://localhost:8001/health   # extractor
curl http://localhost:8002/health   # processor
curl http://localhost:8003/health   # web-api
```

### 2.5 Portas expostas


| Serviço             | Porta | Descrição                            |
| ------------------- | ----- | ------------------------------------ |
| Extractor           | 8001  | Extração Oracle + publicação na fila |
| Processor           | 8002  | De-para + envio ao PR                |
| Web API             | 8003  | Autenticação, emissão, painel        |
| RabbitMQ Management | 15672 | Interface web da fila (guest/guest)  |
| PostgreSQL          | 5432  | Banco operacional                    |


### 2.6 Comandos úteis

```bash
# Ver logs
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f processor-service

# Parar tudo
docker compose down

# Rebuild após alteração de código
docker compose up --build -d
```

---

## 3. Frontend (`site/`)

### 3.1 Instalar dependências

```bash
cd /caminho/para/projeto-nota-fiscal/site

npm install
cp .env.example .env
nano .env
```

### 3.2 Configurar URL da API

No arquivo `site/.env`, use o IP ou hostname da VM:

```env
VITE_API_BASE_URL=http://IP-DA-VM:8003
```

### 3.3 Modo desenvolvimento (teste)

```bash
npm run dev -- --host 0.0.0.0
```

Acesse: `http://IP-DA-VM:5173`

### 3.4 Modo produção (build estático)

```bash
npm run build
# Arquivos gerados em site/dist/
```

Servir os arquivos estáticos (exemplo com `serve`):

```bash
npm install -g serve
serve -s dist -l 5173
```

Para ambiente definitivo, recomenda-se configurar **Nginx** apontando para `site/dist/`.

---

## 4. CORS (acesso ao painel fora de localhost)

Se o site rodar em outro endereço (IP da VM, domínio), ajuste o `web-api-service` no arquivo `api/docker-compose.yml`:

```yaml
- CORS_ORIGINS=http://IP-DA-VM:5173,http://localhost:5173
```

Depois reinicie o serviço:

```bash
cd /caminho/para/projeto-nota-fiscal/api
docker compose up -d web-api-service
```

---

## 5. Oracle Client (se necessário)

Se a conexão com o Tasy exigir Oracle Instant Client na VM:

```bash
sudo apt install -y libaio1
# Instalar Oracle Instant Client conforme documentação da instituição
```

Confirme no `.env`:

- `USE_MOCK_ORACLE=false`
- `ORACLE_DSN` com usuário, senha, host e service name corretos

---

## 6. Credenciais iniciais do painel

Criadas automaticamente no primeiro start do `web-api-service`:


| Campo   | Valor padrão |
| ------- | ------------ |
| Usuário | `admin`      |
| Senha   | `admin123`   |


Altere via `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD` no `.env` ou no `docker-compose.yml`.

---

## 7. Testes rápidos na VM

### Health checks

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Login na API

```bash
curl -X POST http://localhost:8003/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Consultar nota por NR Sequência

```bash
TOKEN="cole-o-access_token-aqui"

curl "http://localhost:8003/notas/consultar?estabelecimento=Castelo&nr_sequencia=12345" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. Resumo dos caminhos


| Ação                     | Comando / caminho                          |
| ------------------------ | ------------------------------------------ |
| Backend + Docker         | `cd api && docker compose up --build -d`   |
| `.env` do backend        | `api/.env`                                 |
| Frontend — instalar deps | `cd site && npm install`                   |
| `.env` do frontend       | `site/.env`                                |
| Frontend — dev           | `cd site && npm run dev -- --host 0.0.0.0` |
| Frontend — build         | `cd site && npm run build`                 |


---

## 9. Fluxo de integração com o PR

1. **De-para de produto:** `GET /Controle/produtos/{codVinculo}` — envia código material Tasy, recebe código PR.
2. **Gravação da NF:** `POST /NF` — payload final com códigos PR nos itens.

O processor usa `PR_ENV=homolog` por padrão. Para produção, altere para `PR_ENV=production` no ambiente do `processor-service`.

> Os endpoints do PR exigem acesso pela rede com **IP fixo** (VM). Fora dessa rede, erros de conexão ou autenticação são esperados.

---

## 10. Documentação complementar

- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md) — operação manual/automática, testes em homolog, comandos do dia a dia
- [api/README.md](./api/README.md) — visão geral da arquitetura e endpoints
- [site/README.md](./site/README.md) — frontend e credenciais
- [api/Documentos_Projeto/README_TASY_PR.md](./api/Documentos_Projeto/README_TASY_PR.md) — contexto do projeto Tasy → PR

