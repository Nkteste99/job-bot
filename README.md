# BOT DE CANDIDATURAS

## Descrição
Projeto para buscar vagas em plataformas públicas, persistir em banco (Supabase/PostgREST), notificar novas vagas via Telegram e automatizar candidaturas.

## Arquitetura resumida
Sites → Coleta (collectors) → Banco (Supabase/PostgREST) → Repositórios (database/) → Serviço de orquestração (services/) → Candidatura automática → Notificação → Telegram

## Pré-requisitos
- Python 3.12
- Docker e docker-compose (opcional)
- Conta Supabase com projeto e API key
- Bot Telegram e chat id (crie um bot com @BotFather e obtenha `TELEGRAM_BOT_TOKEN`)

## Instalação e configuração do `.env`

1. Copie o arquivo de exemplo ou crie um `.env` na raiz do projeto:

```bash
cp .env.example .env
```

2. Valores necessários no `.env`:

- `SUPABASE_URL` — URL do projeto Supabase (ex: https://xyz.supabase.co)
- `SUPABASE_KEY` — anon ou service key do Supabase
- `TELEGRAM_BOT_TOKEN` — token do bot (formato: 123456:ABC-DEF...)
- `TELEGRAM_CHAT_ID` — id do chat ou usuário que receberá mensagens
- `GUPY_COOKIE` — valor do `candidate_secure_token` JWT da sessão autenticada na Gupy (sem o prefixo `candidate_secure_token=`)
- `APRESENTACAO_TEXTO` — texto de apresentação pessoal usado na etapa "Apresente-se!" da candidatura Gupy
- `USER_NAME`, `USER_EMAIL`, `CURRICULO_PDF_PATH` — dados do usuário usados na automação de candidatura

3. Salve o arquivo e mantenha fora do controle de versão (já está no `.gitignore`).

## Como rodar localmente (venv)

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como rodar os testes

```bash
pytest -v
```

Os testes usam mocks e não dependem de Supabase nem da API da Gupy.

## Coleta de vagas

```bash
python -m services.collector_service
```

O serviço executa uma coleta imediata ao iniciar e repete a cada 1 hora. Em modo de testes o limite é de 10 vagas por execução (constante `LIMIT` em `collector_service.py`).

Logs gravados em `logs/collector.log` (diretório criado automaticamente).

## Candidatura automática (V2)

O fluxo de candidatura automática na Gupy cobre as seguintes etapas:

1. Autenticação via `GUPY_COOKIE` (JWT `candidate_secure_token`)
2. Criação da candidatura via API
3. Resposta automática a perguntas da empresa — perguntas conhecidas são respondidas automaticamente pelo banco `respostas_perguntas`; perguntas inéditas pausam e aguardam resposta manual
4. Etapa "Apresente-se!":
   - Envio do texto de apresentação (`APRESENTACAO_TEXTO`)
   - Seleção de skills destacadas: Python, Linux, AWS
   - Conclusão da etapa via endpoint `/complete`

Para candidatar manualmente a uma vaga específica:

```bash
python -m services.apply_service
```

## Como rodar com Docker

```bash
docker compose build --no-cache
docker compose up
```

## Variáveis de ambiente

| Variável | Descrição | Obrigatório |
|---|---|---|
| `SUPABASE_URL` | URL do projeto Supabase | ✅ |
| `SUPABASE_KEY` | Chave anon/service do Supabase | ✅ |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram | ✅ |
| `TELEGRAM_CHAT_ID` | Chat id destino | ✅ |
| `GUPY_COOKIE` | JWT `candidate_secure_token` da sessão Gupy | ✅ |
| `APRESENTACAO_TEXTO` | Texto de apresentação para candidaturas Gupy | ✅ |
| `USER_NAME` | Nome do usuário | ✅ |
| `USER_EMAIL` | E-mail do usuário | ✅ |
| `CURRICULO_PDF_PATH` | Caminho para o PDF do currículo | opcional |
| `LOG_LEVEL` | Nível de logs (default: INFO) | opcional |

## Status do projeto

### V1 — Concluída ✅
- Conexão Supabase e migrações
- Coletor Gupy com deduplicação
- Notificações Telegram formatadas (empresa, modalidade, prazo)
- Agendamento periódico com logs

### V2 — Em andamento 🚧
- ✅ Etapa 1: Mapeamento do fluxo de candidatura Gupy
- ✅ Etapa 2: Candidatura automática via API Gupy
- ✅ Etapa 3: Etapa "Apresente-se!" (texto de apresentação + skills + complete)
- ⏳ Próximas etapas: banco de Q&A dinâmico, integração com outros sites

### V3 — Planejada
- Análise de compatibilidade vaga x perfil com IA (Gemini API)
- Geração de carta de apresentação personalizada
- Leitura e classificação de e-mails de recrutadores
- Resumo inteligente de descrições de vagas

## Observações
- O `GUPY_COOKIE` expira periodicamente — renove fazendo login na Gupy e copiando o novo valor de `candidate_secure_token` nos headers de qualquer requisição autenticada (F12 → Network → Request Headers → Cookie)
- Verifique permissões RLS no Supabase caso inserções não sejam persistidas