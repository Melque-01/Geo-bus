#!/usr/bin/env bash
# Verificação rápida da instalação (rodar dentro da VM).
# Uso: bash scripts/verify_vm.sh [ip]
set -uo pipefail

IP="${1:-127.0.0.1}"
falhas=0

checar() {
    local nome="$1" comando="$2"
    if eval "$comando" >/dev/null 2>&1; then
        echo "OK   $nome"
    else
        echo "FALHA $nome"
        falhas=$((falhas + 1))
    fi
}

echo "== Serviços =="
checar "postgresql ativo" "systemctl is-active --quiet postgresql"
checar "docker ativo" "systemctl is-active --quiet docker"
checar "container osrm rodando" "docker inspect -f '{{.State.Running}}' osrm | grep -qx true"
checar "geo-buss ativo" "systemctl is-active --quiet geo-buss"
checar "geo-buss habilitado no boot" "systemctl is-enabled --quiet geo-buss"

echo "== Banco =="
checar "PostGIS instalado" "sudo -u postgres psql -d geo_buss -tAc 'SELECT postgis_version()'"
checar "tabela rotas" "sudo -u postgres psql -d geo_buss -tAc 'SELECT count(*) FROM rotas'"
checar "índice GIST na geometria" \
    "sudo -u postgres psql -d geo_buss -tAc \"SELECT 1 FROM pg_indexes WHERE indexname='rotas_geometria_idx'\" | grep -q 1"

echo "== OSRM =="
checar "API /route respondendo" \
    "curl -s --max-time 8 'http://127.0.0.1:5000/route/v1/driving/-49.9022,-6.0678;-49.8950,-6.0700?overview=false' | grep -q '\"code\":\"Ok\"'"

echo "== Aplicação =="
checar "GET / (frontend)" "curl -s --max-time 8 'http://${IP}/' | grep -qi 'Geo Buss'"
checar "/api/status banco+osrm" "curl -s --max-time 10 'http://${IP}/api/status' | grep -q '\"banco\": true, \"osrm\": true'"

echo
if [ "${falhas}" -eq 0 ]; then
    echo "TUDO OK"
else
    echo "${falhas} verificação(ões) falharam"
fi
exit "${falhas}"
