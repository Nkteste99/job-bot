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

Instruções finais — executar o projeto completo

- Crie e ative um virtualenv (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
```

- Instale dependências:

```bash
pip install -r requirements.txt
```

- Crie e preencha um arquivo `.env` na raiz com as variáveis obrigatórias (ex.: `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).

- Rodar a coleta única (coleta → persistência → notificações):

```bash
source .venv/bin/activate
python -m services.collector_service
```

- Opcional: agende via `cron` / `systemd` / `docker-compose` conforme seu fluxo de implantação.

Pare aqui e confirme para que eu possa executar novamente ou ajustar algo.
