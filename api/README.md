# ISMS Nota Fiscal Integrator

Projeto de integração de notas fiscais entre o Tasy (origem) e o PR (destino),
com arquitetura baseada em microserviços e um painel web para operação.

## Arquitetura oficial (MVP)

```text
[Oracle Tasy]
      |
      v
[extractor-service] -- publica --> [RabbitMQ: nf.raw] -- consome --> [processor-service] -- POST --> [PR]
                                                                                     |
                                                                                     +--> [PostgreSQL operacional]
                                                                                     +--> [DLQ: nf.dead]

[site (React)] --> [web-api-service] --> aciona extractor / lê status no PostgreSQL
```

## Microserviços

- `extractor-service`
  - Consulta o Tasy de forma periódica (padrão: 6 em 6 minutos).
  - Publica notas em formato canônico na fila `nf.raw`.
  - Possui modo de preview para validar transformação antes do envio.
  - Possui scheduler interno com execução automática configurável por `.env`.
- `processor-service`
  - Consome notas da fila `nf.raw`.
  - Aplica regras de de-para e validações.
  - Envia para endpoint do PR conforme estabelecimento.
  - Trata erros com tentativas e envia falhas para `nf.dead`.
- `web-api-service`
  - Autenticação JWT com papéis `adm` e `usuario`.
  - Administrador emite nota para qualquer estabelecimento e cria usuários.
  - Usuário emite nota apenas do próprio estabelecimento.
  - Aciona a emissão chamando o `extractor-service` e lê o status operacional no PostgreSQL.

## Frontend (site)

- Projeto React + Vite + TypeScript em `../site`.
- Tela de login, emissão de nota e acompanhamento de status.
- Telas por papel (administrador também gerencia usuários).

## Estabelecimentos suportados

Cada estabelecimento possui endpoint e token próprios no PR:

- Castelo
- HRAS
- HRT
- Ponta Pora

## Contrato-base de nota para PR

Formato de referência (Swagger PR):

```json
{
  "nf": "123456",
  "serie": "1",
  "fornecedor": {
    "cnpj": "12345678912345"
  },
  "dataNF": "2026-06-09T11:18:25.607Z",
  "operador": "INTEGRACAO",
  "doacao": false,
  "vencimento": "2026-06-09T11:18:25.639Z",
  "dataRecebimento": "2026-06-09T11:18:25.639Z",
  "desconto": 0,
  "ipi": 0,
  "frete": 0,
  "valorTotal": 400,
  "qtdItens": 1,
  "produtos": [
    {
      "codProd": "63437",
      "cunit": 200,
      "valor": 400,
      "qtdEntrada": 2,
      "loteNF": [
        {
          "lote": "A01",
          "observacao": "Nome Lab 1",
          "qtdLote": 1
        },
        {
          "lote": "A02",
          "validade": "2026-06-09T11:18:25.639Z",
          "observacao": "Nome Lab 2",
          "qtdLote": 1
        }
      ]
    }
  ]
}
```

## Execução local

1. Copie `.env.example` para `.env`.
2. Ajuste endpoints/tokens por estabelecimento.
3. Suba os serviços:

```powershell
docker-compose up --build
```

Serviços:
- extractor: `http://localhost:8001`
- processor: `http://localhost:8002`
- web-api: `http://localhost:8003`
- rabbitmq management: `http://localhost:15672`

Parâmetros de agendamento no `.env`:
- `POLL_INTERVAL_MINUTES`: intervalo do ciclo automático (padrão `6`).
- `EXTRACTION_SCHEDULER_ENABLED`: habilita/desabilita scheduler do extractor.
- `EXTRACTION_RUN_ON_STARTUP`: dispara um ciclo imediato ao subir o serviço.

Parâmetros do painel/web-api no `.env`:
- `JWT_SECRET`, `JWT_EXPIRE_MINUTES`: configuração do token de autenticação.
- `EXTRACTOR_URL`: endereço do extractor usado para acionar a emissão.
- `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`: admin inicial criado no startup.
- `CORS_ORIGINS`: origens permitidas do frontend.

Parâmetros do PR (processor-service):
- `PR_ENV`: `homolog` (padrão) ou `production`.
- Homolog: `PR_BASE_URL_HOMOLOG`, `PR_HOMOLOG_TOKEN` (token único para todos os estabelecimentos).
- Produção: `PR_BASE_URL_PRODUCTION` + tokens por estabelecimento (`PR_CASTELO_TOKEN`, `PR_HRAS_TOKEN`, `PR_HRT_TOKEN`, `PR_PONTA_PORA_TOKEN`).

Fluxo de integração com o PR:
1. De-para de produto: `GET /Controle/produtos/{codVinculo}` — envia código material Tasy, recebe código PR.
2. Gravação da NF: `POST /NF` — payload final com códigos PR nos itens.

> **Nota:** os endpoints do PR exigem acesso pela rede com IP fixo (VM). Localmente o processor tentará homolog; erros de rede são esperados fora da VM.

### Frontend

```bash
cd ../site
npm install
cp .env.example .env
npm run dev
```

Site disponível em `http://localhost:5173`.
Login inicial: `admin` / `admin123` (altere via `.env`).

## Compatibilidade Ubuntu (uso futuro)

O projeto é compatível com Ubuntu e pode ser executado tanto localmente quanto via Docker.

Pontos de atenção no Ubuntu:

- Criar/ativar venv com comandos Linux:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Instalar dependências:
  - `pip install -r requirements.txt`
- Subir stack com Docker Compose:
  - `docker compose up --build`
- Configurar `ORACLE_DSN` no `.env`.
- Caso necessário para Oracle, instalar Oracle Client (quando usar modo thick).

## Endpoints principais

- `GET /health` em todos os serviços.
- `GET /preview?estabelecimento=Castelo` no extractor para validar payloads.
- `POST /run` no extractor para disparo manual sob demanda.
- `POST /auth/login`, `GET /auth/me` no web-api para autenticação.
- `POST /usuarios`, `GET /usuarios` (somente admin) no web-api.
- `POST /notas/emitir`, `GET /notas` no web-api para emissão e acompanhamento.

## Estrutura de pastas

```text
Projeto_ISMS_NF/
  services/
    extractor/         # Extração Oracle, transformação e publicação na fila
    processor/         # Consumo, retry, DLQ e envio ao PR
    web_api/           # Autenticação, usuários, emissão e dados do painel
  docker/
  Documentos_Projeto/
site/                  # Frontend React + Vite + TypeScript
```

As entradas oficiais da aplicação são `services/extractor/main.py`,
`services/processor/main.py` e `services/web_api/main.py`.

## Regras de extração Oracle

Os SQLs oficiais de extração ficam em `services/extractor/sql_templates.py`:

- `build_header_notes_sql(...)` para cabeçalho das notas.
- `build_items_by_nr_sequencia_sql(...)` para itens da nota.
- `LOTS_BY_ITEM_LOTE_SQL` para lotes por item.
- `LOTS_BY_ITEM_FALLBACK_SQL` como fallback de lote.

Os filtros por estabelecimento ficam em `services/extractor/extraction_profiles.py`.
Assim, mudanças futuras de data mínima, código de estabelecimento e critérios de recorte (incluindo `cd_operacao_nf`) podem ser feitas sem alterar o fluxo principal.
