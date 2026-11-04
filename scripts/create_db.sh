#!/usr/bin/env bash
# Cria usuário/banco do Geo Buss, habilita PostGIS e aplica o schema.
# Não altera listen_addresses (o firewall controla o acesso externo).
# Uso: sudo bash scripts/create_db.sh "senha-do-banco"
set -euo pipefail

if [ "$#" -lt 1 ] || [ -z "$1" ]; then
    echo "informe a senha do usuário ${USUARIO:-geo_buss}: sudo bash scripts/create_db.sh \"senha\"" >&2
    exit 1
fi

SENHA="$1"
BANCO="geo_buss"
USUARIO="geo_buss"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="${SCRIPT_DIR}/../db/schema.sql"

echo "==> Papel ${USUARIO}"
if [ "$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${USUARIO}'")" = "1" ]; then
    sudo -u postgres psql -c "ALTER ROLE ${USUARIO} WITH LOGIN PASSWORD '${SENHA}'" >/dev/null
else
    sudo -u postgres psql -c "CREATE ROLE ${USUARIO} LOGIN PASSWORD '${SENHA}'" >/dev/null
fi

echo "==> Banco ${BANCO}"
if [ "$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${BANCO}'")" = "1" ]; then
    echo "já existe"
else
    sudo -u postgres createdb -O "${USUARIO}" "${BANCO}"
fi

echo "==> Extensão PostGIS"
sudo -u postgres psql -d "${BANCO}" -c "CREATE EXTENSION IF NOT EXISTS postgis" >/dev/null

echo "==> Ajuste de posse (caso as tabelas tenham sido criadas pelo postgres)"
sudo -u postgres psql -d "${BANCO}" -q -c "ALTER TABLE IF EXISTS rotas OWNER TO ${USUARIO}" 2>/dev/null || true
sudo -u postgres psql -d "${BANCO}" -q -c "ALTER SEQUENCE IF EXISTS rotas_id_seq OWNER TO ${USUARIO}" 2>/dev/null || true

echo "==> Schema (aplicado como ${USUARIO} para manter a posse das tabelas)"
PGPASSWORD="${SENHA}" psql -h 127.0.0.1 -U "${USUARIO}" -d "${BANCO}" -q -f "${SCHEMA}"

echo "==> Verificação"
sudo -u postgres psql -d "${BANCO}" -c "SELECT postgis_version() AS postgis"
PGPASSWORD="${SENHA}" psql -h 127.0.0.1 -U "${USUARIO}" -d "${BANCO}" \
    -c "SELECT count(*) AS rotas FROM rotas"
