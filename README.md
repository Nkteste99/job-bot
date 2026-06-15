BOT DE CANDIDATURAS

Descrição
---------
Projeto para buscar vagas em plataformas públicas, persistir em banco (Supabase/PostgREST) e notificar novas vagas via Telegram.

Arquitetura resumida
--------------------
Sites → Coleta (collectors) → Banco (Supabase/PostgREST) → Repositórios (database/) → Serviço de orquestração (services/) → Notificação → Telegram

Pré-requisitos
--------------
- Python 3.12
- Docker e docker-compose (opcional)
- Conta Supabase com projeto e API key
- Bot Telegram e chat id (crie um bot com @BotFather e obtenha `TELEGRAM_BOT_TOKEN`)

Instalação e configuração do `.env`
----------------------------------
1. Copie o arquivo de exemplo (se houver) ou crie um `.env` na raiz do projeto.

```bash
cp .env.example .env || true
# Edite .env e preencha as variáveis sensíveis
```

2. Valores mínimos necessários no `.env`:

- `SUPABASE_URL` — URL do projeto Supabase (ex: https://xyz.supabase.co)
- `SUPABASE_KEY` — anon ou service key do Supabase
- `TELEGRAM_BOT_TOKEN` — token do bot (formato: 123456:ABC-DEF...)
- `TELEGRAM_CHAT_ID` — id do chat ou usuário que receberá mensagens

3. Salve o arquivo e mantenha fora do controle de versão (adicione ao `.gitignore`).

Como rodar localmente (venv)
---------------------------
1. Criar e ativar um virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:

```bash
pip install -r requirements.txt
```

Como rodar os testes
--------------------
Com o virtualenv ativado e as dependências instaladas:

```bash
pytest
```

Para saída mais detalhada:

```bash
pytest -v
```

Os testes usam mocks e não dependem de Supabase nem da API da Gupy.

3. Rodar o serviço de coleta (executa coleta, persiste e envia notificações):

```bash
python -m services.collector_service
```

Agendamento periódico
---------------------
O serviço pode ser executado continuamente com agendamento horário (usa a biblioteca `schedule`). Ao iniciar o serviço ele executa uma coleta imediata e então roda a coleta a cada 1 hora (no modo de testes o número de vagas por execução é limitado a 10).

Exemplo — rodar em foreground:

```bash
source .venv/bin/activate
python -m services.collector_service
```

Observações:
- Para alterar o limite de vagas por execução edite a constante `LIMIT` no início de `services/collector_service.py` ou remova a lógica de slice quando quiser coletar todas as vagas.
- Logs: o serviço grava logs em `logs/collector.log` no diretório do projeto (o diretório `logs/` é criado automaticamente).
- Para execução em produção use um gerenciador de processos (systemd, supervisord, Docker, etc.) ou crie um container com `docker compose`.

Como rodar com Docker
---------------------
1. Configure as variáveis de ambiente no ambiente do container (ou monte o arquivo `.env`).
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
- `USER_NAME`, `USER_EMAIL`, `CURRICULO_PDF_PATH`: dados do usuário usados por integrações/automação de candidatura (opcionais).
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
  - Notificações via Telegram integradas (`notifier/telegram.py`) — enviam resumo e mensagens por vaga com empresa, modalidade e salário provisório

Formato das mensagens do Telegram
---------------------------------
- Empresa: tenta `companyName` quando disponível e usa `careerPageName` como fallback
- Modalidade: `remote` vira `🏠 Remoto`, `hybrid` vira `🔄 Híbrido` e os demais casos aparecem como `🏢 Presencial`
- Salário: por enquanto a notificação mostra `⚠️ Salário: Não informado`

Observações
-----------
- A coleta depende da disponibilidade das APIs públicas (por exemplo Gupy). Em testes recentes o endpoint público retornou 404 em algumas consultas; ajustar termos/filtros pode ser necessário.
- Verifique permissões RLS no Supabase caso inserções não sejam persistidas.

Próximos passos sugeridos
------------------------
- Agendar execução periódica (cron/systemd/docker) para rodar a coleta regularmente.
- Expandir cobertura de testes para outros repositórios e serviços.

Se desejar, eu executo agora uma coleta de teste com outro termo ou ajusto o coletor; informe a ação desejada.
