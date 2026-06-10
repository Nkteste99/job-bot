PROJETO 2 — JOB APPLICATION BOT

Descrição

Sistema automatizado para busca, análise, organização e candidatura em vagas de emprego.

Objetivo

- Buscar vagas em múltiplas plataformas
- Filtrar vagas compatíveis com o perfil do usuário
- Armazenar histórico de candidaturas
- Automação de candidaturas quando permitido
- Notificações via Telegram

Estrutura inicial gerada para V1.

Setup rápido com Docker (V1)
---------------------------

1. Copie e edite as variáveis de ambiente:

```bash
cp .env.example .env
# Edit .env and fill values (SUPABASE_URL, SUPABASE_KEY, TELEGRAM_...)
```

2. Build and run with docker-compose:

```bash
docker compose build --no-cache
docker compose up
```

3. Desenvolvendo localmente (opcional):

```bash
# Install dependencies locally (optional)
python -m pip install -r requirements.txt
python main.py
```

Notas
- A primeira versão não conecta ao Supabase automaticamente; configure as variáveis em `.env`.
- As etapas seguintes implementarão conexão com banco, coletores e notificações.
