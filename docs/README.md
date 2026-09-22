# Documentação — Integração de Notas Fiscais (Tasy → PR)

Índice da pasta `docs/`. Use a pasta certa conforme o público.

| Pasta | Público | Conteúdo |
|-------|---------|----------|
| [`cliente/`](./cliente/) | Cliente / operação de negócio | Processo, regras, manual do painel |
| [`dev/`](./dev/) | Desenvolvedores / ops | Arquitetura, instalação, deploy, operação técnica |
| [`erros/`](./erros/) | Plantão / ferias | Erros recorrentes e troubleshooting |
| [`arquivo/`](./arquivo/) | Histórico | Documentos legados (não usar como referência atual) |
| [`assets/`](./assets/) | — | Logos |

## Comece por aqui

### Cliente
1. [PROCESSO_E_REGRAS.md](./cliente/PROCESSO_E_REGRAS.md) — fluxo, retry de **2 dias**, status, papéis  
2. Manual DOCX do painel (gerado) — `cliente/Manual_Cliente_Painel_Integracao_Notas_Fiscais.docx`  
3. Documentação de projeto DOCX — `cliente/Documentacao_Projeto_Integracao_Notas_Fiscais.docx`

### Dev / plantão
1. [DOCUMENTACAO_TECNICA.md](./dev/DOCUMENTACAO_TECNICA.md)  
2. [ERROS_RECORRENTES.md](./erros/ERROS_RECORRENTES.md) ← **use nas férias**  
3. [DEBUG_VM.md](./erros/DEBUG_VM.md) · [DEBUG_PR_SQLSERVER.md](./erros/DEBUG_PR_SQLSERVER.md)

### Regenerar DOCX
```bash
cd docs/cliente && python gerar_manual_cliente.py
cd docs/cliente && python gerar_documentacao_projeto_cliente.py
cd docs/dev && python gerar_documentacao_tecnica.py
```
