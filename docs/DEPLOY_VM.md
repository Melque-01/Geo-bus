# Deploy: W11 (desenvolvimento) → VM Ubuntu (entrega)

Regra do trabalho: **tudo roda na VM** (frontend, app, banco PostGIS e OSRM).
De fora, só o IP da VM responde — porta 80.

```
                 Wi-Fi 192.168.1.0/24
   W11 (dev)  ──────────────┐
   192.168.1.188            │
                            ▼
                   VM Ubuntu (bridged)
                   192.168.1.149
                   ├─ :80    app + frontend (única porta exposta)
                   ├─ :5000  OSRM        (127.0.0.1)
                   └─ :5432  PostGIS     (127.0.0.1)
```

## Fase 1 — desenvolver no Windows 11

Duas opções:

**A. App no W11, serviços na VM** (recomendado; menos coisa local)

1. VM com PostGIS + OSRM já configurados (fases 2 e 3 abaixo).
2. `.env` no W11:

```
DB_HOST=192.168.1.149
OSRM_URL=http://192.168.1.149:5000
PORTA=8000
```

3. `python app.py` → http://127.0.0.1:8000

**B. Tudo local no W11**: Docker Desktop com `postgis/postgis` e `osrm/osrm-backend`,
usando os mesmos scripts como referência. Mais pesado, só se precisar trabalhar offline.

## Fase 2 — rede da VM (VirtualBox, bridged)

Feito neste projeto:

```powershell
VBoxManage modifyvm "ubunto" `
  --nic1 bridged `
  --bridgeadapter1 "MediaTek Wi-Fi 6 MT7921 Wireless LAN Card" `
  --nictype1 virtio
```

Dentro da VM, conferir:

```bash
ip -br a
# enp0s3 UP 192.168.1.149/24
ip route
ping -c2 192.168.1.1
```

Se não pegar IP:

```bash
sudo netplan get
ls /etc/netplan/
sudo netplan apply
sudo dhclient -v enp0s3
```

Para o IP não mudar (professor acessa por IP), duas saídas:

- reserva DHCP no roteador para o MAC `08:00:27:9D:FB:20` (mais simples), ou
- IP fixo em `/etc/netplan/99-geo-buss.yaml` (arquivo versionado em
  `deploy/netplan-geo-buss.yaml`):

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: false
      mtu: 1400
      addresses: [192.168.1.149/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
```

```bash
sudo chmod 600 /etc/netplan/99-geo-buss.yaml
sudo netplan apply
```

> Wi-Fi com isolamento de cliente (AP isolation) quebra o bridged. Sintoma: VM sem
> DHCP/ARP. Alternativa: NAT + port forwarding `80 → 8000` no VirtualBox, acessando
> por `http://192.168.1.188`.

## Fase 3 — serviços na VM

Copie o projeto para a VM:

```powershell
scp -r "C:\Users\melqu\projetos\geo buss" melque@192.168.1.149:/tmp/geo-buss
```

Na VM:

```bash
sudo mkdir -p /opt/geo-buss && sudo cp -r /tmp/geo-buss/* /opt/geo-buss/
cd /opt/geo-buss

sudo bash scripts/create_db.sh 'senha-forte'
bash scripts/setup_osrm.sh
sudo bash scripts/deploy_app.sh
```

`deploy_app.sh` cria `/opt/geo-buss/.env` a partir de `.env.vm` (banco e OSRM em
`127.0.0.1`), monta a venv, instala `psycopg` e habilita o serviço
`geo-buss.service` escutando na porta 80 (`CAP_NET_BIND_SERVICE`, sem root).

## Fase 4 — firewall (só 80 sai)

```bash
sudo ufw allow 22/tcp     # administração
sudo ufw allow 80/tcp     # aplicação (única porta pública)
sudo ufw enable
sudo ufw status verbose
```

Portas 5000 e 5432 não vão para a rede em geral. Para o desenvolvimento no W11
(seções acima) elas são liberadas só para o IP dele:

```bash
sudo ufw allow from 192.168.1.188 to any port 5432 proto tcp
sudo ufw allow from 192.168.1.188 to any port 5000 proto tcp
```

## Fase 5 — verificação

```bash
curl http://127.0.0.1/api/status          # {"banco": true, "osrm": true}
sudo systemctl status geo-buss
sudo docker ps --filter name=osrm
```

Do W11 ou de outra máquina da rede:

```
http://192.168.1.149/
```

## Atualizar o sistema depois de mudar código

```powershell
scp -r "C:\Users\melqu\projetos\geo buss" melque@192.168.1.149:/tmp/geo-buss
```

```bash
sudo bash /opt/geo-buss/scripts/deploy_app.sh
```

## Checklist de entrega

- [ ] VM com IP fixo (ou reserva DHCP) acessível de outra máquina
- [ ] PostGIS com PostGIS habilitado e tabela `rotas`
- [ ] OSRM com extrato de Parauapebas respondendo em `127.0.0.1:5000`
- [ ] `geo-buss.service` habilitado (`systemctl is-enabled geo-buss`)
- [ ] `GET /api/status` → `{"banco": true, "osrm": true}`
- [ ] Frontend abrindo pelo IP da VM, mapa e cálculo dos 4 tempos
- [ ] ufw liberando apenas 22 e 80
