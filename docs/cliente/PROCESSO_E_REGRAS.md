# Processo e regras de negócio — Integração de Notas Fiscais

**Público:** cliente (Instituto Mais Saúde) e operação de negócio.  
**Versão:** setembro/2026  

Documento de referência do **processo**. O passo a passo das telas está no *Manual do Cliente* (DOCX).

---

## 1. Objetivo

Automatizar e controlar o envio de notas fiscais de **entrada** do **Tasy** para o **PR** (estoque/materiais), com:

- Extração automática ou manual  
- Registro de sucesso e erro  
- Marcação da nota no Tasy após sucesso (`dt_integracao`)  
- Alertas por e-mail  
- Painel web para acompanhamento e reemissão  

Estabelecimentos: **Castelo**, **HRAS**, **HRT (Itaituba)**, **Ponta Porã**.

---

## 2. Fluxo resumido

1. O sistema busca no Tasy notas elegíveis (sem data de integração).  
2. Aplica regras de negócio (tipo, operação, datas, itens, local de estoque).  
3. Valida de-para de materiais e lote, quando aplicável.  
4. Envia a nota ao PR.  
5. **Sucesso:** status *Enviado (sent)* e grava integração no Tasy.  
6. **Falha:** classifica o erro, tenta novamente conforme a regra abaixo e permite **reemissão manual**.  
7. E-mail periódico resume pendências/erros por unidade (destinatários **ativos**).

---

## 3. Tentativas automáticas (retry) — regra vigente

Esta é a regra que deve constar nas comunicações e treinamentos:

| Situação | O que o sistema faz |
|----------|---------------------|
| Erros de **negócio** (ex.: sem de-para, sem lote, retorno PR de validação) | Poucas tentativas automáticas rápidas; depois vai para **falha definitiva**. |
| Erros de **indisponibilidade / lentidão do PR** (timeouts, circuit breaker) | Pode continuar tentando por até **2 dias corridos** a partir da primeira tentativa. |
| Após esgotar o prazo ou as tentativas | Status **Falha definitiva (`dead_letter`)**. A nota **sai da fila automática**. |
| Depois da falha definitiva | Somente **Reemitir** no painel, **depois** de corrigir a causa. |

**Por quê 2 dias?** Evita que notas com PR instável fiquem reprocessando sem fim e congestionem a operação. O que não integrar nesse prazo fica visível como falha definitiva para tratamento manual.

---

## 4. Status no painel

| Status | Significado |
|--------|-------------|
| Pendente (`pending`) | Entrou no fluxo; ainda não concluiu |
| Enviado (`sent`) | Integrada com sucesso no PR |
| Aguardando retry (`retry_pending`) | Falhou; ainda há tentativa automática prevista |
| Falha definitiva (`dead_letter`) | Esgotou tentativas/prazo; exige ação (reemitir após correção) |

---

## 5. Tipos de erro comuns

| Tipo | Significado | Ação típica |
|------|-------------|-------------|
| Sem de-para | Material Tasy sem vínculo no PR | Cadastrar de-para e reemitir |
| Sem lote | Item exige lote e não veio no Tasy | Corrigir no Tasy e reemitir |
| Retorno PR | PR recusou (validação, já existente etc.) | Ler mensagem; corrigir se necessário |
| Timeout PR | PR/banco lento ou indisponível | Aguardar estabilização; se virar falha definitiva, reemitir depois |

Caso especial: mensagem de **NF + fornecedor já existente no PR** é tratada como integrada (sucesso).

---

## 6. Papéis de acesso

| Perfil | Escopo |
|--------|--------|
| Administrador global (`adm`) | Todas as unidades; configurações; usuários |
| Administrador local (`adm_local`) | Usuários e e-mails da própria unidade |
| Usuário (`usuario`) | Operação da própria unidade |
| Dev (interno GHR) | Operação + auditoria técnica e filas |

Recuperação de senha: usuário com **e-mail cadastrado** usa “Esqueci minha senha” no login (código por e-mail).

Destinatários de relatório: podem ser **inativados** (deixam de receber sem apagar o cadastro). Não há exclusão na interface.

---

## 7. Elegibilidade (resumo)

- Tipo entrada (EN); sem `dt_integracao` no Tasy  
- Operações liberadas: 1 e 39 (itens da operação 33 desconsiderados)  
- Datas mínimas de emissão / atualização de estoque conforme perfil da unidade  
- Local de estoque 104 não elegível  
- Pelo menos um item elegível após os filtros  

Detalhes operacionais de tela: ver Manual do Cliente.

---

## 8. Boas práticas para o cliente

1. Corrigir de-para/lote **antes** de reemitir em massa.  
2. Em período de instabilidade do PR, preferir emitir **nota específica** de teste.  
3. Acompanhar Dashboard e e-mails; falhas definitivas precisam de dono na unidade.  
4. Manter e-mails dos usuários e destinatários atualizados e ativos.  
5. Ligar/desligar scheduler e relatório por unidade em **Configurações** (admin global).

---

## 9. Contato técnico

Problemas de infraestrutura, filas ou timeout do PR: acionar o suporte técnico GHR com NF, nr sequência, estabelecimento e horário aproximado.
