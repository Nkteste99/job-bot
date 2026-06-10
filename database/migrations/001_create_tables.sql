-- 001_create_tables.sql
-- Creates tables `vagas` and `candidaturas` for the job-bot project.

-- Table: vagas
CREATE TABLE IF NOT EXISTS vagas (
    id SERIAL PRIMARY KEY,
    external_id TEXT,
    empresa TEXT,
    titulo TEXT,
    link TEXT,
    salario TEXT,
    localizacao TEXT,
    fonte TEXT,
    fonte TEXT,
    data_publicacao TIMESTAMPTZ,
    descricao TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Table: candidaturas
CREATE TABLE IF NOT EXISTS candidaturas (
    id SERIAL PRIMARY KEY,
    vaga_id INTEGER REFERENCES vagas(id) ON DELETE CASCADE,
    data_aplicacao TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'Encontrada',
    observacoes TEXT,
    ultima_atualizacao TIMESTAMPTZ,
    origem TEXT,
    tentativas INTEGER DEFAULT 0,
    erro_ultima_tentativa TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
