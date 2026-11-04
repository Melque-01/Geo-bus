# Instalação da VM (Ubuntu Server) — PostgreSQL/PostGIS + OSRM

Alvo: Ubuntu Server 22.04 LTS ou 24.04 LTS.
Dados de mapa: **Parauapebas/PA**.
Responsabilidades: banco (PostGIS) e OSRM (geometria/distância). O cálculo de
tempo por perfil roda na aplicação Python.

Exemplo de rede usada abaixo:

| Máquina | IP | Porta |
|---|---|---|
| VM Ubuntu | `192.168.0.10` | 5432 (Postgres), 5000 (OSRM) |
| PC (app) | `192.168.0.20` | 8000 (app) |

Troque os IPs e senhas pelos seus.

---

## 1. Pacotes base

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql postgresql-contrib postgis osmium-tool curl \
                    docker.io docker-compose-v2
sudo systemctl enable --now postgresql docker
```

## 2. Banco

```bash
sudo -u postgres psql <<'SQL'
CREATE USER geo_buss WITH PASSWORD 'senha-forte-aqui';
CREATE DATABASE geo_buss OWNER geo_buss;
SQL

sudo -u postgres psql -d geo_buss -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d geo_buss -c "SELECT postgis_full_version();"
```

Aplicar o schema (uma vez, do PC ou copiando o arquivo). O script do projeto já
faz tudo — papel, banco, PostGIS e schema com a posse correta:

```bash
sudo bash scripts/create_db.sh "senha-do-banco"
```

Manualmente seria:

```bash
psql "postgresql://geo_buss:senha-forte-aqui@192.168.0.10:5432/geo_buss" -f db/schema.sql
```

A aplicação também aplica `db/schema.sql` na subida, se o banco estiver acessível.

## 3. Liberar acesso remoto ao Postgres

`/etc/postgresql/16/main/postgresql.conf` (ajuste a versão se diferente):

```
listen_addresses = '*'
```

`/etc/postgresql/16/main/pg_hba.conf` — no final do arquivo:

```
host    geo_buss    geo_buss    192.168.0.20/32    scram-sha-256
```

```bash
sudo systemctl restart postgresql
sudo ufw allow from 192.168.0.20 to any port 5432 proto tcp
```

Teste do PC: `psql "postgresql://geo_buss:senha@192.168.0.10:5432/geo_buss" -c "SELECT 1"`

## 4. Dados do OSM (recorte de Parauapebas)

Geofabrik não tem extract por cidade; o caminho mais curto é baixar a região
Norte (≈153 MB) e recortar com `osmium`.

```bash
mkdir -p ~/osrm && cd ~/osrm
curl -O https://download.geofabrik.de/south-america/brazil/norte-latest.osm.pbf

# Bounding box aproximada do núcleo urbano de Parauapebas:
#   sul, oeste, norte, leste
osmium extract -b -6.20,-50.05,-5.95,-49.75 \
    -o parauapebas.osm.pbf norte-latest.osm.pbf

osmium fileinfo -e parauapebas.osm.pbf | head -n 20
```

Para ampliar a área, aumente a bbox (o município é grande). Confira a caixa em
<https://boundingbox.klokantech.com> antes de gerar o recorte.

Atualização periódica (opcional):

```bash
cd ~/osrm && curl -O https://download.geofabrik.de/south-america/brazil/norte-latest.osm.pbf
osmium extract -b -6.20,-50.05,-5.95,-49.75 -o parauapebas.osm.pbf norte-latest.osm.pbf --overwrite
# depois repita o passo 5 (extract/partition/customize) e reinicie o container
```

## 5. Subir o OSRM (perfil driving)

```bash
cd ~/osrm

sudo docker run --rm -v ~/osrm:/data ghcr.io/project-osrm/osrm-backend \
    osrm-extract -p /opt/car.lua /data/parauapebas.osm.pbf

sudo docker run --rm -v ~/osrm:/data ghcr.io/project-osrm/osrm-backend \
    osrm-partition /data/parauapebas.osrm

sudo docker run --rm -v ~/osrm:/data ghcr.io/project-osrm/osrm-backend \
    osrm-customize /data/parauapebas.osrm

sudo docker run -d --name osrm --restart unless-stopped -p 5000:5000 \
    -v ~/osrm:/data ghcr.io/project-osrm/osrm-backend \
    osrm-routed --algorithm mld /data/parauapebas.osrm
```

Se a imagem do GHCR não estiver disponível, use `osrm/osrm-backend` (Docker Hub).

Teste:

```bash
curl "http://127.0.0.1:5000/route/v1/driving/-49.9022,-6.0678;-49.8950,-6.0700?overview=false"
```

Resposta esperada: `{"code":"Ok", ...}`.

> Nota: um único perfil (`car.lua`) serve de base geométrica. Moto usa a mesma
> geometria da via (com velocidade própria); bicicleta e a pé usam a mesma malha
> viária. Para geometria específica de ciclovia/calçada seria necessário um
> segundo OSRM com `bicycle.lua` / `foot.lua` em outra porta.

## 6. Firewall da VM

```bash
sudo ufw allow from 192.168.0.20 to any port 5000 proto tcp
sudo ufw allow from 192.168.0.20 to any port 8000 proto tcp   # app rodando na VM
sudo ufw status verbose
```

## 7. Rodar a aplicação na VM (systemd)

```bash
sudo apt install -y python3-venv
sudo mkdir -p /opt/geo-buss && sudo chown $USER:$USER /opt/geo-buss
# copie o projeto para /opt/geo-buss (scp/rsync/git)
cd /opt/geo-buss
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # edite com IP/senha reais
```

`/etc/systemd/system/geo-buss.service`:

```ini
[Unit]
Description=Geo Buss
After=network.target postgresql.service docker.service

[Service]
User=SEU_USUARIO
WorkingDirectory=/opt/geo-buss
EnvironmentFile=/opt/geo-buss/.env
ExecStart=/opt/geo-buss/.venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now geo-buss
sudo journalctl -u geo-buss -f
```

## 8. Verificação final

```bash
curl http://192.168.0.10:8000/api/status
curl http://192.168.0.10:8000/api/perfis
curl -X POST http://192.168.0.10:8000/api/rota \
  -H "content-type: application/json" \
  -d '{"origem":"-6.0678,-49.9022","destino":"-6.0700,-49.8950"}'
```

`/api/status` deve devolver `{"banco": true, "osrm": true}`.
Abra no navegador: `http://192.168.0.10:8000`.

## 9. Ajuste das velocidades

O tempo vem de `distancia_km / velocidade_kmh * 60`, com as velocidades de
`config.PERFIS` (sobrescrevíveis no `.env`):

| Perfil | Padrão |
|---|---|
| carro | 30 km/h |
| moto | 35 km/h |
| bicicleta | 15 km/h |
| a pé | 4,8 km/h |

Calibre com medições reais do trânsito de Parauapebas e reinicie o serviço
(`sudo systemctl restart geo-buss`).

## 10. Problemas comuns

| Sintoma | Causa provável | Correção |
|---|---|---|
| `/api/status` com `banco: false` | `pg_hba.conf` / firewall / senha | revise passos 2 e 3 |
| `/api/status` com `osrm: false` | container parado | `sudo docker logs osrm`, suba de novo |
| `sem rota entre os pontos` | pontos fora do recorte | amplie a bbox e regenere (passo 4) |
| OSRM morre ao subir | faltam arquivos `.osrm.partition`/`.osrm.cells` | rode `osrm-partition` e `osrm-customize` |
| build do OSRM sem memória | extrato grande | recorte a bbox ou aumente RAM/swap |
