# Painel NF (frontend)

Interface web do projeto de integração de notas fiscais (Tasy → PR).

Stack: React + Vite + TypeScript.

## Funcionalidades

- Tela de login (autenticação via JWT no `web-api-service`).
- Papéis:
  - **Administrador**: emite nota para qualquer um dos 4 estabelecimentos e cria novos usuários.
  - **Usuário**: emite nota apenas do próprio estabelecimento.
- Acompanhamento do status das notas processadas.

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
