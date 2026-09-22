# Painel NF (frontend)

Interface web do projeto de integração de notas fiscais (Tasy → PR).

Stack: React + Vite + TypeScript.

## Funcionalidades

- Tela de login (autenticação via JWT no `web-api-service`).
- Papéis: `adm`, `adm_local`, `usuario`, `dev` (detalhes em `docs/dev/DOCUMENTACAO_TECNICA.md`).
- Recuperação de senha por e-mail (“Esqueci minha senha”).
- Acompanhamento do status das notas processadas.

Documentação: [`docs/README.md`](../docs/README.md).

## Rodando localmente

Pré-requisito: Node.js 18+.

```bash
cd site
npm install
cp .env.example .env   # ajuste VITE_API_BASE_URL se necessário
npm run dev
```

Acesse `http://localhost:5173`.

O backend (`web-api-service`) deve estar rodando em `http://localhost:8003`
(veja o `docker-compose.yml` na raiz do projeto `Projeto_ISMS_NF`).

## Credenciais iniciais

Um administrador é criado automaticamente pelo backend no primeiro start:

- usuário: `admin`
- senha: `admin123`

Altere via variáveis `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`.
