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

Como executar a coleta

5. Teste rápido

Depois de configurar o token e o chat id, você pode testar envio de mensagem diretamente usando um REPL Python:

```py
from notifier.telegram import send_message
send_message('Teste do bot: coleta configurada')
```

Se receber a mensagem no Telegram, o envio está funcionando.
1. Configure as variáveis em `.env` (SUPABASE_URL e SUPABASE_KEY) e ative um ambiente Python com dependências instaladas ou use Docker.

2. Rodar o serviço de coleta manualmente:

```bash
# activate your venv if using one
python -m services.collector_service
```

O serviço executa uma coleta para `desenvolvedor` em `São Paulo` quando executado como script. Para testar idempotência, execute o comando duas vezes; a segunda execução não deve inserir vagas duplicadas.

Observação: os resultados dependem das credenciais e das políticas do Supabase (RLS). Se as inserções parecerem não persistir, verifique as permissões do projeto Supabase.
JOB APPLICATION BOT

Descrição
---------
Projeto para buscar vagas em plataformas públicas, persistir em banco (Supabase/PostgREST) e notificar novas vagas via Telegram.

Arquitetura resumida
--------------------
Sites → Coleta (collectors) → Banco (Supabase/PostgREST) → Repositórios (database/) → Serviço de orquestração (services/) → Notificação → Telegram

Pré-requisitos
--------------
- Python 3.12
- Docker & docker-compose (opcional)
- Conta Supabase com projeto e API key
- Bot Telegram e chat id (crie um bot com @BotFather e obtenha `TELEGRAM_BOT_TOKEN`)

Instalação e configuração do `.env`
----------------------------------
1. Copie o modelo e preencha valores sensíveis:

```bash
cp .env .env.local || true
# Edite .env.local ou .env com seus valores
```

2. Variáveis essenciais a configurar no arquivo `.env` (ex.: `./.env`):

- `SUPABASE_URL` — URL do projeto Supabase (ex: https://xyz.supabase.co)
- `SUPABASE_KEY` — anon ou service key do Supabase
- `TELEGRAM_BOT_TOKEN` — token do bot (formato: 123456:ABC-DEF...)
- `TELEGRAM_CHAT_ID` — id do chat ou usuário que receberá mensagens

Veja a seção "Variáveis de ambiente" abaixo para mais detalhes.

Como rodar localmente (venv)
---------------------------
1. Criar e ativar virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Rodar o serviço de coleta (coleta → persistência → notificações):

```bash
python -m services.collector_service
```

Como rodar com Docker
---------------------
1. Configure variáveis de ambiente (p.ex. via arquivo `.env` ou variáveis de ambiente do Docker).
2. Build e run:

```bash
docker compose build --no-cache
docker compose up
```

Variáveis de ambiente (explicação)
---------------------------------
- `SUPABASE_URL`: URL do projeto Supabase (obrigatório para persistência).
- `SUPABASE_KEY`: chave anon/service do Supabase (obrigatório).
- `TELEGRAM_BOT_TOKEN`: token do bot Telegram (obrigatório para notificações).
- `TELEGRAM_CHAT_ID`: chat id destino (obrigatório para notificações).
- `USER_NAME`, `USER_EMAIL`, `CURRICULO_PDF_PATH`: dados de usuário usados por integrações/automação de candidatura (opcionais).
- `LOG_LEVEL`: nível de logs (default `INFO`).
- `PYTHONUNBUFFERED`: útil em containers (default `1`).

Status atual do projeto (V1)
----------------------------
- V1 em desenvolvimento. Etapas concluídas:
	- Cliente Supabase e teste de conexão
	- Arquivo de migração inicial (database/migrations/001_create_tables.sql)
	- Repositórios para `vagas` e `candidaturas` (database/)
	- Coletor Gupy implementado (`collectors/gupy.py`) com mapeamento para `Vaga`
	- Serviço de orquestração de coleta e deduplicação (`services/collector_service.py`)
	- Notificações via Telegram integradas (`notifier/telegram.py`) — enviam resumo e mensagens por vaga

Observações
-----------
- A coleta depende de disponibilidade das APIs públicas (por exemplo Gupy). Em testes recentes o endpoint público retornou 404 em algumas consultas; ajustar termos/filtros pode ser necessário.
- Verifique permissões RLS no Supabase caso inserções não sejam persistidas.

Próximos passos sugeridos
------------------------
- Agendar execução periódica (cron/systemd/docker) para rodar a coleta regularmente.
- Adicionar testes automatizados e cobertura para os repositórios.

Se quiser, eu executo agora uma coleta de teste com outro termo ou ajusto o coletor; confirme qual ação prefere.
