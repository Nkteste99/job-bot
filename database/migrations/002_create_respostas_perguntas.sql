-- 002_create_respostas_perguntas.sql
-- Respostas conhecidas para perguntas customizadas das vagas Gupy.

CREATE TABLE IF NOT EXISTS respostas_perguntas (
    id SERIAL PRIMARY KEY,
    pergunta TEXT NOT NULL,
    resposta TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
