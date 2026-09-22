# Go-live em produção — Integração de Notas Fiscais

Checklist do que precisa ser feito **além** de trocar credenciais Oracle/PR, e como tratar o PostgreSQL na virada.

Complementa: [DEPLOY_NGINX_HTTP.md](./DEPLOY_NGINX_HTTP.md), [DOCUMENTACAO_TECNICA.md](./DOCUMENTACAO_TECNICA.md), [OPERACAO_SCHEDULER_E_EMAIL.md](./OPERACAO_SCHEDULER_E_EMAIL.md).

---

## 1. Resumo

Trocar só usuário/senha Oracle e token PR **não** basta. Em produção é preciso:

1. Desligar mocks e apontar PR para produção  
2. Fortalecer autenticação do painel (`JWT_SECRET`, senha admin)  
3. Rebuild do frontend com a URL da API de produção  
4. CORS, SMTP e destinatários  
5. Preferir **Postgres limpo** (sem dados de homologação)  
6. Validar scheduler, write-back Tasy e um fluxo ponta a ponta

---

## 2. Variáveis e configuração (API)

Arquivo típico: `api/.env` (ou variáveis no host / compose).

| Item | Homolog / dev | Produção (recomendado) |
|------|---------------|------------------------|
| `USE_MOCK_ORACLE` | pode ser `true` | **`false`** |
| Credenciais Oracle | homolog | produção (host, service, user, password) |
| `PR_ENV` | homolog / sandbox | **`production`** |
| Credenciais / URLs PR | ambiente de teste | produção |
| `JWT_SECRET` | valor de teste | **segredo longo e aleatório** (novo) |
| Senha do admin do painel | padrão de lab | **trocar na primeira sessão** |
| `CORS_ORIGINS` | `localhost` | origem real do painel (ex.: `http://painel-isms-nf.ddns.net:5001`) |
| SMTP (`SMTP_*`) | opcional / teste | servidor real + remetente |
| Filas RabbitMQ | defaults ok | manter nomes; ambiente isolado |

Outros pontos:

- Confirmar estabelecimentos e `estabelecimento_config` (scheduler ligado/desligado, horários, flags de relatório).
- Cadastrar **destinatários** de e-mail por unidade no painel (aba Destinatários).
- Não reutilizar o mesmo `JWT_SECRET` de homolog se o painel já foi exposto.

---

## 3. Frontend (site)

Build de produção com a URL da API que o navegador vai chamar:

```bash
cd site
# Exemplo com nginx na porta 5001 (proxy /api → web-api)
set VITE_API_BASE_URL=http://painel-isms-nf.ddns.net:5001/api
npm ci
npm run build
```

Deploy do `site/dist` conforme [DEPLOY_NGINX_HTTP.md](./DEPLOY_NGINX_HTTP.md).

Após mudar `VITE_*`, é obrigatório **rebuild** — variável embutida no bundle.

Logo do projeto: `site/public/logo_isms.png` (também em `docs/assets/` e cópia na raiz `logo_isms.png`).

---

## 4. PostgreSQL: zerar ou manter?

### Recomendação: **zerar** na virada para produção

Motivos:

- Status e histórico de notas de homologação misturam com produção  
- Tabela `nota_report_envio` controla “já enviou no relatório”; dados de teste poluem o relatório real  
- Usuários/senhas/JWT de lab não devem ir para o cliente final  
- Estabelecimentos e configs de teste podem divergir do cadastro real

### Como zerar (Docker Compose na pasta `api/`)

**Atenção:** apaga o volume `pgdata` e **todos** os dados do Postgres desse compose.

```bash
cd api
docker compose down -v
# sobe de novo; migrations/schema sobem com os serviços
docker compose up -d
```

Se o volume tiver outro nome, confira com `docker volume ls` e remova o volume do projeto antes do `up`.

### Quando manter o banco

Só faz sentido se homologação já for o ambiente “quase produção” com:

- mesmos estabelecimentos e usuários finais  
- sem notas de teste que não devam aparecer  
- sem histórico de envio de e-mail que atrapalhe o relatório

Nesse caso, ainda assim revise: admin, `JWT_SECRET`, SMTP, flags de scheduler e limpeza manual de notas de teste se necessário.

---

## 5. Checklist de go-live

### Infra e rede

- [ ] VM / host com Docker e compose estáveis  
- [ ] Nginx (ou equivalente) servindo `site/dist` e proxy `/api` → `8003`  
- [ ] Firewall / DDNS / porta publicada (ex.: 5001) conforme o desenho de deploy  
- [ ] `www-data` (ou usuário do nginx) consegue ler o path do `dist` (permissões na cadeia de pastas)

### Dados e serviços

- [ ] Postgres limpo **ou** banco revisado (ver seção 4)  
- [ ] RabbitMQ saudável; filas `nf.raw` / `nf.dead` ok  
- [ ] `extractor`, `processor`, `web-api`, `report` up  
- [ ] Oracle produção acessível a partir do extractor (rede, Instant Client, credenciais)  
- [ ] PR produção: autenticação e endpoint de NF ok

### Segurança e painel

- [ ] `USE_MOCK_ORACLE=false`  
- [ ] `PR_ENV=production`  
- [ ] `JWT_SECRET` novo e forte  
- [ ] Admin com senha forte; usuários operacionais criados  
- [ ] `CORS_ORIGINS` só com origem(ns) do painel  
- [ ] Site rebuild com `VITE_API_BASE_URL` correto  
- [ ] Login no painel; menu e permissões (admin vs usuário) ok

### Operação

- [ ] Estabelecimentos e config de scheduler conferidos  
- [ ] Destinatários de e-mail cadastrados  
- [ ] SMTP testado (envio real ou teste controlado)  
- [ ] Extração manual de uma nota conhecida  
- [ ] Processamento até status integrado / erro esperado  
- [ ] Write-back `dt_integracao` no Tasy após sucesso no PR  
- [ ] Relatório por e-mail (se ligado) sem duplicar indevidamente  
- [ ] Dashboard / export CSV se forem usados no dia a dia

### Pós go-live (primeiros dias)

- [ ] Monitorar logs dos containers e fila dead  
- [ ] Acompanhar notas em erro (`sem_depara`, `sem_lote`, `retorno_pr`)  
- [ ] Confirmar volume de integração vs expectativa do negócio  
- [ ] Backup do volume Postgres / política de retenção

---

## 6. Ordem sugerida no dia da virada

1. Parar scheduler / evitar extrações em massa durante a janela  
2. `docker compose down -v` (se for Postgres limpo) e subir stack com `.env` de produção  
3. Criar admin/usuários e configs de estabelecimento  
4. Rebuild e publicar o site  
5. Teste ponta a ponta com **poucas** notas  
6. Ligar scheduler e comunicar operação  
7. Monitorar 24–48 h

---

## 7. Rollback rápido

- Voltar `.env` / compose para o ambiente anterior e `docker compose up -d`  
- Republicar `site/dist` da build anterior  
- Se o Postgres de produção já tiver dados reais, **não** rode `down -v` no rollback sem backup

Backup preventivo do volume (exemplo):

```bash
docker run --rm -v api_pgdata:/data -v "%CD%":/backup alpine \
  tar czf /backup/pgdata-backup-$(date +%Y%m%d).tgz -C /data .
```

(Ajuste o nome do volume com `docker volume ls`.)

---

## 8. Referências

| Documento | Uso |
|-----------|-----|
| [DEPLOY_NGINX_HTTP.md](./DEPLOY_NGINX_HTTP.md) | Publicar painel HTTP + proxy API |
| [DEBUG_VM.md](./DEBUG_VM.md) | Problemas na VM (porta, permissões) |
| [OPERACAO_E_TESTES.md](./OPERACAO_E_TESTES.md) | Fluxos de teste |
| [OPERACAO_SCHEDULER_E_EMAIL.md](./OPERACAO_SCHEDULER_E_EMAIL.md) | Scheduler e relatório |
| [DOCUMENTACAO_TECNICA.md](./DOCUMENTACAO_TECNICA.md) | Arquitetura e APIs |
| Manual do cliente (`docs/`) | Uso do painel pelo time operacional |
