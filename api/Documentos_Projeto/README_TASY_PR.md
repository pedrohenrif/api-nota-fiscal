# Tasy PR Integrador de Notas

## Contexto

Este documento consolida a arquitetura oficial do projeto para integração de notas fiscais entre Tasy e PR.

Decisão validada: operar com **dois microserviços** desacoplados por fila.

## Objetivo

Extrair notas fiscais emitidas no Tasy (Oracle), publicar para processamento assíncrono e enviar ao PR conforme regras de de-para por estabelecimento.

## Fluxo oficial

```text
Oracle (Tasy) -> extractor-service -> RabbitMQ (nf.raw) -> processor-service -> Endpoint PR
                                                              |
                                                              +-> PostgreSQL (status operacional)
                                                              +-> RabbitMQ (nf.dead)
```

## Serviços

### extractor-service

- Polling periódico configurável (`POLL_INTERVAL_MINUTES`, padrão 6).
- Consulta notas pendentes no Tasy.
- Publica mensagens canônicas na fila `nf.raw`.

### processor-service

- Consome mensagens da fila `nf.raw`.
- Executa de-para e validações de negócio.
- Envia para PR com token e endpoint por estabelecimento.
- Registra status operacional (sucesso/falha).
- Em caso de falha, encaminha para fila `nf.dead`.

## Estabelecimentos

Cada estabelecimento possui endpoint/token dedicados no PR e regras de de-para próprias:

- Castelo
- HRAS
- HRT
- Ponta Pora

## Contrato de envio ao PR

Formato base acordado com o Swagger PR:

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

## Padrões definidos

- Nomenclatura de serviços: `extractor-service` e `processor-service`.
- Fila primária: `nf.raw`.
- Fila de falhas: `nf.dead`.
- Logs com foco operacional (sem persistência de XML completo).
- Idempotência por combinação de `estabelecimento + nf + serie`.

## Riscos e pontos de atenção

- Validar query Oracle para capturar apenas notas novas (watermark confiável).
- Formalizar regras de de-para por estabelecimento.
- Formalizar política de retry (tentativas e backoff).
- Definir tratamento para retornos negativos do PR.

## Próximos passos do MVP

1. Implementar conector Oracle real no extractor.
2. Implementar consumer contínuo com retry no processor.
3. Criar mapeamentos por estabelecimento.
4. Expor endpoint de reprocessamento por nota.
5. Iniciar painel operacional para monitoramento.
# Tasy PR Middleware

## Visão Geral

O projeto **Tasy PR Middleware** tem como objetivo realizar a integração entre o sistema Tasy e o sistema PR através de uma arquitetura baseada em API middleware.

O sistema será responsável por:

- Extrair notas fiscais do sistema Tasy
- Estruturar e transformar os dados
- Realizar o envio para o sistema PR via endpoint POST
- Monitorar status dos envios
- Permitir disparos automáticos e manuais
- Não armazenar permanentemente dados fiscais sensíveis

---

# Objetivos do Projeto

## Objetivo Principal

Criar uma plataforma de integração robusta, escalável e de fácil manutenção para automatizar o envio de notas fiscais entre os sistemas envolvidos.

## Objetivos Técnicos

- Centralizar a lógica de integração
- Padronizar payloads fiscais
- Reduzir falhas operacionais
- Facilitar auditoria e monitoramento
- Permitir futura expansão para novas integrações
- Garantir segurança e rastreabilidade operacional

---

# Arquitetura Inicial

## Fluxo Principal

```text
[Tasy Database/API]
        ↓
[Serviço de Extração]
        ↓
[Camada DePara / Mapeamento]
        ↓
[Middleware API]
        ↓
[Endpoint PR]
        ↓
[Resposta de sucesso/erro]
```

---

# Estrutura de Módulos

## 1. Módulo de Extração

Responsabilidades:

- Consultar notas pendentes
- Buscar dados no banco/API do Tasy
- Separar notas por estabelecimento
- Preparar payload inicial

## 2. Módulo DePara (Mapeamento)

Responsável por:

- Padronização dos dados
- Centralização de regras fiscais
- Reaproveitamento dos deparas existentes

### Estrutura sugerida

```text
/mappings
    cfop_mapping.json
    produto_mapping.json
    imposto_mapping.json
```

Ou:

```python
class NotaFiscalMapper:
    pass
```

## 3. Serviço de Envio

Responsável por:

- Autenticação via token
- Controle de timeout
- Retry automático
- Logs operacionais
- Controle multi-estabelecimento

## 4. Scheduler Automático

Execução automática a cada 5 minutos.

### Opções avaliadas

- APScheduler
- Celery + Redis (futuro)

## 5. Painel Administrativo

Funcionalidades previstas:

- Dashboard operacional
- Consulta de logs
- Reenvio manual
- Monitoramento de falhas
- Visualização de status

## 6. Estratégia de Logs

O sistema NÃO armazenará dados fiscais completos.

Somente dados operacionais:

- ID da nota
- Timestamp
- Status
- Código de retorno
- Tempo de execução

---

# Tecnologias Definidas

## Backend

- Python
- FastAPI
- SQLAlchemy
- Poetry

## Banco de Dados

- PostgreSQL
- Uso apenas operacional

## Scheduler

- APScheduler

## Logs

- Loguru
- Logging padrão Python

## Infraestrutura futura

- RabbitMQ
- Redis
- Prometheus
- Grafana

---

# Estrutura Atual do Projeto

```text
project/
│
├── services/
│   ├── extractor/
│   └── processor/
├── Documentos_Projeto/
├── docker/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# Estratégias Técnicas

## Multi-tenant

Cada estabelecimento possuirá:

- Token próprio
- Endpoint próprio
- Controle individual de envio

## Retry Controlado

Estratégia inicial:

- 3 tentativas
- Intervalo de 30 segundos

## Idempotência

Objetivo:

Evitar duplicidade no envio de notas fiscais.

Sugestão:

```text
hash(nota + estabelecimento)
```

## Segurança

- HTTPS obrigatório
- Secrets via `.env`
- Tokens segregados
- Logs mascarados

---

# Estratégia de Desenvolvimento

## Fase 1 — MVP Técnico

- Extração de notas
- Serviço de envio
- Scheduler
- Logs básicos
- Estrutura inicial do middleware

## Fase 2 — Operacional

- Painel administrativo
- Dashboard
- Retry avançado
- Consulta operacional

## Fase 3 — Escalabilidade

- Filas resilientes
- Tempo real
- Observabilidade
- Monitoramento avançado

---

# Estratégia Arquitetural

Foi definida a utilização de uma única API centralizada para simplificar:

- Manutenção
- Diagnóstico de erros
- Monitoramento
- Escalabilidade futura

A arquitetura será orientada a serviços e preparada para futuras expansões.

---

# Requisitos Não Funcionais

- Alta disponibilidade
- Facilidade de manutenção
- Escalabilidade
- Segurança operacional
- Baixo acoplamento
- Facilidade de auditoria

---

# Possíveis Expansões Futuras

O middleware poderá futuramente atuar como um:

## Motor de Integração

Permitindo integrações como:

- Tasy → PR
- Tasy → Outro ERP
- Tasy → Prefeitura
- Tasy → APIs terceiras

---

# Processo de Desenvolvimento

## Ferramentas

- Git
- Poetry
- Docker
- Cursor AI

## Organização

- Desenvolvimento modular
- Versionamento Git
- Documentação contínua
- Padronização de código

---

# Observações Importantes

- O sistema NÃO será um ERP
- O middleware NÃO armazenará XMLs fiscais completos
- O foco inicial é velocidade de entrega e estabilidade
- A documentação será tratada como parte obrigatória do projeto

---

# Status Atual

Projeto em fase inicial de estruturação técnica e definição arquitetural.

Próximos passos:

1. Criação do repositório Git
2. Estrutura inicial do projeto
3. Definição dos endpoints
4. Criação do scheduler
5. Implementação do módulo de extração
6. Implementação do serviço de envio
