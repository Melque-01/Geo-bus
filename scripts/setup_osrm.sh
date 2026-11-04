#!/usr/bin/env bash
# Baixa o extrato OSM, recorta Parauapebas e sobe o OSRM em Docker.
# Uso: bash scripts/setup_osrm.sh [bbox]
#   bbox no formato do osmium: oeste,sul,leste,norte (lon,lat)
#   padrão do núcleo urbano de Parauapebas: -50.05,-6.20,-49.75,-5.95
set -euo pipefail

BBOX="${1:--50.05,-6.20,-49.75,-5.95}"
DIR="${HOME}/osrm"
IMAGEM="ghcr.io/project-osrm/osrm-backend"
PBF_RECORTE="${DIR}/parauapebas.osm.pbf"

mkdir -p "${DIR}"
cd "${DIR}"

echo "==> Pacotes"
sudo apt-get update -y
sudo apt-get install -y osmium-tool curl docker.io

if [ ! -s "${DIR}/norte-latest.osm.pbf" ]; then
    echo "==> Baixando extrato Norte (~154 MB)"
    rm -f "${DIR}/norte-latest.osm.pbf"
    curl -L --fail --retry 3 -o norte-latest.osm.pbf \
        https://download.geofabrik.de/south-america/brazil/norte-latest.osm.pbf
fi

echo "==> Recortando bbox ${BBOX}"
osmium extract -b "${BBOX}" --overwrite -o "${PBF_RECORTE}" norte-latest.osm.pbf
osmium fileinfo -e "${PBF_RECORTE}" | head -n 15

echo "==> Processando (extract/partition/customize)"
sudo docker run --rm -v "${DIR}:/data" "${IMAGEM}" \
    osrm-extract -p /opt/car.lua /data/parauapebas.osm.pbf
sudo docker run --rm -v "${DIR}:/data" "${IMAGEM}" \
    osrm-partition /data/parauapebas.osrm
sudo docker run --rm -v "${DIR}:/data" "${IMAGEM}" \
    osrm-customize /data/parauapebas.osrm

echo "==> Subindo container (porta 5000)"
sudo docker rm -f osrm >/dev/null 2>&1 || true
sudo docker run -d --name osrm --restart unless-stopped -p 5000:5000 \
    -v "${DIR}:/data" "${IMAGEM}" osrm-routed --algorithm mld /data/parauapebas.osrm

sleep 5
echo "==> Teste"
curl -s "http://127.0.0.1:5000/route/v1/driving/-49.9022,-6.0678;-49.8950,-6.0700?overview=false" \
    | head -c 400
echo
