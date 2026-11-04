#!/usr/bin/env bash
# Instala a aplicação na VM e registra o serviço systemd.
# Uso (na VM, com o projeto já copiado para /opt/geo-buss):
#   sudo bash scripts/deploy_app.sh
set -euo pipefail

DESTINO="/opt/geo-buss"
USUARIO="${SUDO_USER:-$USER}"
ORIGEM="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Copiando projeto para ${DESTINO}"
sudo mkdir -p "${DESTINO}"
if [ "${ORIGEM}" != "${DESTINO}" ]; then
    sudo rsync -a --delete \
        --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '.env' \
        "${ORIGEM}/" "${DESTINO}/"
fi
sudo chown -R "${USUARIO}:${USUARIO}" "${DESTINO}"

echo "==> Ambiente virtual"
sudo apt-get install -y python3-venv
if [ ! -d "${DESTINO}/.venv" ]; then
    sudo -u "${USUARIO}" python3 -m venv "${DESTINO}/.venv"
fi
sudo -u "${USUARIO}" "${DESTINO}/.venv/bin/pip" install --upgrade pip
sudo -u "${USUARIO}" "${DESTINO}/.venv/bin/pip" install -r "${DESTINO}/requirements.txt"

if [ ! -f "${DESTINO}/.env" ]; then
    echo "==> Criando .env (edite se necessário)"
    sudo -u "${USUARIO}" cp "${DESTINO}/.env.vm" "${DESTINO}/.env"
fi

echo "==> Serviço systemd"
sudo sed "s|__USUARIO__|${USUARIO}|g; s|__DESTINO__|${DESTINO}|g" \
    "${DESTINO}/deploy/geo-buss.service" | sudo tee /etc/systemd/system/geo-buss.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now geo-buss
sleep 2
sudo systemctl --no-pager --full status geo-buss | head -n 15

echo "==> Teste"
curl -s http://127.0.0.1/api/status || echo "sem resposta ainda"
echo
