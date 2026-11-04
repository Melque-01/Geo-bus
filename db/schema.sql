-- Schema do Geo Buss (PostgreSQL + PostGIS)
-- Aplicar com: psql -h HOST -U USUARIO -d geo_buss -f db/schema.sql

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS rotas (
    id              BIGSERIAL PRIMARY KEY,
    origem          GEOMETRY(Point, 4326) NOT NULL,
    destino         GEOMETRY(Point, 4326) NOT NULL,
    geometria       GEOMETRY(LineString, 4326) NOT NULL,
    distancia_m     DOUBLE PRECISION NOT NULL CHECK (distancia_m >= 0),
    duracao_osrm_s  DOUBLE PRECISION,
    tempos          JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rotas_criado_em_idx ON rotas (criado_em DESC);
CREATE INDEX IF NOT EXISTS rotas_geometria_idx ON rotas USING GIST (geometria);
CREATE INDEX IF NOT EXISTS rotas_origem_idx    ON rotas USING GIST (origem);
CREATE INDEX IF NOT EXISTS rotas_destino_idx   ON rotas USING GIST (destino);

COMMENT ON TABLE rotas IS 'Histórico de rotas calculadas (OSRM) com tempos por perfil.';
COMMENT ON COLUMN rotas.tempos IS 'Tempo estimado por perfil: {"carro": {"tempo_min": 8.2, ...}, ...}';
