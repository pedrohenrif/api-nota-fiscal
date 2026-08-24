# Deploy na nuvem com Nginx (HTTP, sem SSL)

Guia para publicar o painel ISMS NF em uma VM com **nginx na porta 80**, ainda **sem certificado HTTPS**.  
Quando houver domínio e SSL, use a seção final (Certbot).

Complementa:

- [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md)
- [DEBUG_VM.md](./DEBUG_VM.md)
- [OPERACAO_SCHEDULER_E_EMAIL.md](./OPERACAO_SCHEDULER_E_EMAIL.md)

Arquivo de exemplo do nginx: [deploy/nginx-isms-nf.conf](./deploy/nginx-isms-nf.conf)

---

## Visão geral

```text
Internet → :80 nginx
              ├─ /        → frontend estático (site/dist)
              └─ /api/    → web-api Docker (127.0.0.1:8003)
```

| Serviço | Expor na internet? |
|---------|--------------------|
| nginx `:80` | Sim |
| web-api `:8003` | Não (só localhost, via proxy) |
| extractor / processor / report | Não |
| Postgres / RabbitMQ | Não |
| Oracle | Não |

---

## 1. Pré-requisitos na VM

```bash
sudo apt update
sudo apt install -y nginx
node -v   # precisa de Node para build do site
npm -v
docker -v
docker compose version
```

Firewall (exemplo UFW):

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
# Não abrir 8001–8004, 5432, 5672 para a internet
sudo ufw enable
sudo ufw status
```

---

## 2. Código e stack Docker

```bash
cd /caminho/para/projeto-nota-fiscal
git pull

cd api
docker compose up -d
```

### 2.1 API só em localhost (recomendado)

No `api/docker-compose.yml`, no serviço `web-api-service`, use:

```yaml
ports:
  - "127.0.0.1:8003:8003"
```

Em vez de `"8003:8003"` (que publica na rede).

```bash
docker compose up -d --force-recreate web-api-service
curl -s http://127.0.0.1:8003/health
```

Esperado: `{"status":"ok","service":"web_api"}`.

---

## 3. Variáveis da API (`api/.env`)

Ajuste o CORS para a URL pública do painel (HTTP):

```env
CORS_ORIGINS=http://SEU_IP_OU_NOME
```

Se for acessar por IP e por nome:

```env
CORS_ORIGINS=http://203.0.113.10,http://painel.seudominio.com
```

Reinicie:

```bash
docker compose restart web-api-service
```

---

## 4. Build do site

O `VITE_API_BASE_URL` é embutido **no build**. Tem que apontar para o proxy `/api`.

```bash
cd /caminho/para/projeto-nota-fiscal/site
```

Arquivo `site/.env`:

```env
VITE_API_BASE_URL=http://SEU_IP_OU_NOME/api
```

Exemplos:

```env
VITE_API_BASE_URL=http://203.0.113.10/api
# ou, com DNS:
VITE_API_BASE_URL=http://painel.seudominio.com/api
```

```bash
npm install
npm run build
# gera site/dist
ls dist
```

Sempre que mudar IP/nome ou `VITE_API_BASE_URL`, rode `npm run build` de novo.

---

## 5. Configurar Nginx

```bash
sudo cp /caminho/para/projeto-nota-fiscal/deploy/nginx-isms-nf.conf \
  /etc/nginx/sites-available/isms-nf

sudo nano /etc/nginx/sites-available/isms-nf
```

Altere:

- `server_name` → IP ou nome
- `root` → caminho absoluto de `site/dist`

Ative:

```bash
sudo ln -sf /etc/nginx/sites-available/isms-nf /etc/nginx/sites-enabled/isms-nf
# se o default ocupar a porta 80:
sudo rm -f /etc/nginx/sites-enabled/default

sudo nginx -t
sudo systemctl reload nginx
```

Testes locais na VM:

```bash
curl -s http://127.0.0.1/api/health
curl -I http://127.0.0.1/
```

No navegador: `http://SEU_IP_OU_NOME`

---

## 6. DNS (nome sem SSL ainda)

No provedor de DNS:

| Tipo | Nome | Valor |
|------|------|--------|
| A | `painel` (ou `@`) | IP público da VM |

Depois atualize:

1. `api/.env` → `CORS_ORIGINS=http://painel.seudominio.com`
2. `site/.env` → `VITE_API_BASE_URL=http://painel.seudominio.com/api`
3. nginx `server_name painel.seudominio.com;`
4. `cd site && npm run build`
5. `docker compose restart web-api-service` (em `api/`)
6. `sudo nginx -t && sudo systemctl reload nginx`

---

## 7. Checklist de problemas

| Sintoma | O que checar |
|---------|----------------|
| Site abre, API 404 | `curl http://127.0.0.1/api/health` e bloco `location /api/` |
| Erro de CORS no browser | `CORS_ORIGINS` igual à URL do site (com `http://`) |
| Login chama `localhost:8003` | Rebuild do site com `VITE_API_BASE_URL` correto |
| Tela branca no refresh de rota | `try_files ... /index.html` no nginx |
| IP na auditoria “errado” | headers `X-Forwarded-For` / `X-Real-IP` no proxy |

---

## 8. Depois: HTTPS com Let's Encrypt

Quando o domínio apontar para a VM:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d painel.seudominio.com
```

Em seguida:

1. `CORS_ORIGINS=https://painel.seudominio.com`
2. `VITE_API_BASE_URL=https://painel.seudominio.com/api`
3. `npm run build` no `site`
4. `docker compose restart web-api-service`
5. Confirme redirecionamento HTTP → HTTPS no nginx

---

## 9. Operação do dia a dia

```bash
# Atualizar código
cd /caminho/para/projeto-nota-fiscal
git pull
cd api && docker compose up -d --force-recreate web-api-service report-service

# Rebuild front (se mudou site/)
cd ../site && npm run build
sudo systemctl reload nginx
```

Logs:

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
cd /caminho/para/projeto-nota-fiscal/api
docker compose logs -f web-api-service
```

---

## 10. Caso atual — DDNS + porta 5001

Dados da infra:

| Item | Valor |
|------|--------|
| DDNS | `painel-isms-nf.ddns.net` |
| Porta pública | `5001` |
| URL do painel | `http://painel-isms-nf.ddns.net:5001` |
| URL da API (via nginx) | `http://painel-isms-nf.ddns.net:5001/api` |

### 10.1 Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 5001/tcp
sudo ufw enable
sudo ufw status
```

Confirme com a infra se o NAT/firewall externo também publica **5001 → IP da VM:5001**.

### 10.2 API (`api/.env`)

```env
CORS_ORIGINS=http://painel-isms-nf.ddns.net:5001
```

```bash
cd /caminho/para/projeto-nota-fiscal/api
# web-api só em localhost:
# ports: - "127.0.0.1:8003:8003"
docker compose up -d
docker compose restart web-api-service
curl -s http://127.0.0.1:8003/health
```

### 10.3 Build do site (`site/.env`)

```env
VITE_API_BASE_URL=http://painel-isms-nf.ddns.net:5001/api
```

```bash
cd /caminho/para/projeto-nota-fiscal/site
npm install
npm run build
```

### 10.4 Nginx na 5001

```bash
sudo cp /caminho/para/projeto-nota-fiscal/deploy/nginx-isms-nf.conf \
  /etc/nginx/sites-available/isms-nf
sudo nano /etc/nginx/sites-available/isms-nf
# ajuste o root=.../site/dist
sudo ln -sf /etc/nginx/sites-available/isms-nf /etc/nginx/sites-enabled/isms-nf
sudo nginx -t
sudo systemctl reload nginx
```

Testes:

```bash
curl -s http://127.0.0.1:5001/api/health
curl -I http://127.0.0.1:5001/
# de fora / do seu PC:
curl -s http://painel-isms-nf.ddns.net:5001/api/health
```

Abrir no navegador: **http://painel-isms-nf.ddns.net:5001**

### 10.5 Se não abrir de fora

1. `sudo ss -tlnp | grep 5001` — nginx escutando?
2. `sudo ufw status` — 5001 liberada?
3. Perguntar à infra se o DDNS aponta para o IP certo e se o NAT da 5001 está ativo
4. `nslookup painel-isms-nf.ddns.net` — resolve para o IP da VM?
