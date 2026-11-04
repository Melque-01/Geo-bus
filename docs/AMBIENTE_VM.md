# Ambiente real da VM (estado configurado)

Registro do que existe hoje na VM — não repetir os comandos sem necessidade.

## Identificação

| Item | Valor |
|---|---|
| Hypervisor | VirtualBox 7.2.22 (VM `ubunto`) |
| SO | Ubuntu 26.04.1 LTS, kernel 7.0.0-42 |
| Hostname / usuário | `ubunto` / `melque` |
| vCPU / RAM / disco | 5 / 4 GB / 25 GB (19 GB livres) |
| IP (fixo) | `192.168.1.149/24`, gateway `192.168.1.1` |
| Interface | `enp0s3`, MAC `08:00:27:9d:fb:20`, virtio, MTU 1400 |
| Fuso | `America/Sao_Paulo` |

Esta é uma VM **nova, instalada do zero** (a antiga `Clone de Ubuntu Server`
usava a faixa `192.168.0.x` e não existe mais). O notebook agora está na faixa
`192.168.1.x`.

## Rede (o que foi feito e por quê)

1. A VM nova veio com `nic1 NAT` (`10.0.2.15`), o que impede qualquer acesso
   externo. Trocado para **bridged** no adaptador do notebook
   (MediaTek Wi-Fi 6 MT7921) e NIC `e1000` → `virtio`.
2. `/etc/netplan/99-geo-buss.yaml` fixa `192.168.1.149/24` (arquivo versionado
   em `deploy/netplan-geo-buss.yaml`), com `mtu: 1400`.
3. Configuração de rede do cloud-init desativada
   (`/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg`) e
   `/etc/netplan/50-cloud-init.yaml` removido, para não haver gateway duplicado.
4. MTU 1400 mantido: no bridge Wi-Fi do notebook, pacotes de 1500 não passam
   (blackhole). Diagnóstico: `ping -M do -s 1472 1.1.1.1` falha, `-s 1400` passa.

## O que foi instalado (tudo do zero)

| Item | Detalhe |
|---|---|
| PostgreSQL | 18.6 (`postgresql-18`) |
| PostGIS | 3.6.2 (`postgresql-18-postgis-3`) |
| Banco | `geo_buss`, dono `geo_buss`, senha em `/opt/geo-buss/.env` |
| Schema | `db/schema.sql` aplicado (tabela `rotas` + índices GIST) |
| Docker | 29.1.3 (`docker.io`), habilitado no boot |
| OSRM | imagem `ghcr.io/project-osrm/osrm-backend`, container `osrm`, porta 5000 |
| Dados OSM | `/root/osrm/parauapebas.osm.pbf` (727 KB, recorte do Norte) |
| App | `/opt/geo-buss`, venv `.venv`, systemd `geo-buss.service` na porta 80 |
| Firewall | ufw: 22 e 80 abertos; 5432/5000 só para o W11 (`192.168.1.188`) |
| SSH | `openssh-server` instalado e habilitado |

Não existem nesta VM os serviços da antiga (apache2, mediamtx, tailscale).

## URLs

- Aplicação (professor / rede local): `http://192.168.1.149/`
- Status: `http://192.168.1.149/api/status` → `{"banco": true, "osrm": true}`
- OSRM (somente dentro da VM, ou liberado para o W11): `http://127.0.0.1:5000`

## Desenvolvimento no W11 (app local, serviços na VM)

```powershell
.\.venv\Scripts\python.exe app.py     # usa o .env local (127.0.0.1:8000)
```

O `.env` do W11 aponta `DB_HOST`/`OSRM_URL` para `192.168.1.149`. Para isso:

- ufw na VM: `5432/tcp` e `5000/tcp` liberados só para `192.168.1.188` (W11)
- `pg_hba.conf`: `host geo_buss geo_buss 192.168.1.188/32 scram-sha-256`
- `listen_addresses = '*'` no `postgresql.conf` (o ufw controla quem entra)

Nenhuma outra máquina da rede alcança Postgres nem OSRM.

## Instalação do zero (resumo do que foi executado)

```bash
# 1. pacotes
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgis osmium-tool \
                    curl python3-venv docker.io ufw rsync openssh-server
sudo systemctl enable --now postgresql docker

# 2. rede
sudo install -m 600 /tmp/99-geo-buss.yaml /etc/netplan/99-geo-buss.yaml
sudo netplan apply

# 3. projeto + banco
sudo mkdir -p /opt/geo-buss && sudo tar -xzf /tmp/geo-buss.tar.gz -C /opt/geo-buss
sudo chown -R melque:melque /opt/geo-buss
sudo bash /opt/geo-buss/scripts/create_db.sh '<senha-do-banco>'

# 4. OSRM (baixa o Norte, recorta e sobe o container)
sudo bash /opt/geo-buss/scripts/setup_osrm.sh

# 5. aplicação (venv, .env, systemd na porta 80)
sudo bash /opt/geo-buss/scripts/deploy_app.sh

# 6. firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow from 192.168.1.188 to any port 5432 proto tcp
sudo ufw allow from 192.168.1.188 to any port 5000 proto tcp
sudo ufw --force enable
```

## Operação

```bash
sudo systemctl status geo-buss
sudo journalctl -u geo-buss -f
sudo docker logs osrm --tail 50
sudo systemctl restart geo-buss
```

## Atualizar o código a partir do W11

```powershell
# no W11, dentro do projeto
tar -czf "$env:TEMP\geo-buss.tar.gz" --exclude=.venv --exclude=__pycache__ --exclude=.git .
.\.venv\Scripts\python.exe tools\vm.py put "$env:TEMP\geo-buss.tar.gz" "/tmp/geo-buss.tar.gz"
.\.venv\Scripts\python.exe tools\vm.py sudo "tar -xzf /tmp/geo-buss.tar.gz -C /opt/geo-buss && chown -R melque:melque /opt/geo-buss && systemctl restart geo-buss"
```

`tools/vm.py` usa `paramiko` (só no W11, `requirements-dev.txt`) e lê
`VM_HOST`, `VM_USER` e `VM_PASSWORD` do ambiente (não há valores padrão).

## Atualizar o mapa (quando houver mudanças nas vias)

```bash
sudo bash /opt/geo-buss/scripts/setup_osrm.sh
```

O script rebaixa o extrato Norte, recorta a bbox de Parauapebas, refaz
extract/partition/customize e reinicia o container.

> **Atenção à ordem da bbox no osmium**: `oeste,sul,leste,norte` (lon,lat),
> ou seja `-50.05,-6.20,-49.75,-5.95`. Inverter gera recorte vazio e o OSRM
> falha com `There are no edges remaining after parsing`.
>
> O recorte atual cobre o núcleo urbano (~727 KB de PBF). Pontos fora dele
> são recusados pela API com 400 (`fora da área de Parauapebas`). Para ampliar,
> passe uma bbox maior **e** ajuste `AREA_BBOX` no `.env`:
> `sudo bash /opt/geo-buss/scripts/setup_osrm.sh "-50.20,-6.35,-49.60,-5.80"`

## Verificação

```bash
bash /opt/geo-buss/scripts/verify_vm.sh              # na própria VM
bash /opt/geo-buss/scripts/verify_vm.sh 192.168.1.149
```

Checa serviços, PostGIS, índice GIST, container OSRM e os endpoints da aplicação.
