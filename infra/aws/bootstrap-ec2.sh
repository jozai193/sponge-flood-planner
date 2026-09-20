#!/usr/bin/env bash
set -euxo pipefail

exec > >(tee /var/log/sponge-bootstrap.log | logger -t sponge-bootstrap -s 2>/dev/console) 2>&1
export DEBIAN_FRONTEND=noninteractive

PUBLIC_IP="__SPONGE_PUBLIC_IP__"
HOSTNAME_FQDN="$PUBLIC_IP.sslip.io"

until curl --fail --silent --show-error --connect-timeout 3 https://github.com/ >/dev/null; do
  sleep 10
done

apt-get update
apt-get install --yes --no-install-recommends ca-certificates curl docker-compose-v2 docker.io git openssl
systemctl enable --now docker

if [ ! -f /swapfile ]; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
fi

install -d -m 0755 /opt/sponge
git clone --filter=blob:none https://github.com/jozai193/sponge-flood-planner.git /opt/sponge/app
git -C /opt/sponge/app fetch --depth 1 origin 04ea05db041fee75439066ab84ffa9055f60a3ca
git -C /opt/sponge/app checkout --detach 04ea05db041fee75439066ab84ffa9055f60a3ca

DB_PASSWORD="$(openssl rand -hex 32)"
umask 077
printf '%s\n' \
  "SPONGE_DB_PASSWORD=$DB_PASSWORD" \
  "SPONGE_TRUSTED_HOSTS=$HOSTNAME_FQDN" \
  "SPONGE_TRUSTED_PROXY_CIDRS=127.0.0.1/32" \
  "SPONGE_PUBLIC_PORT=8080" \
  > /opt/sponge/app/.env.aws

cd /opt/sponge/app
docker compose --env-file .env.aws -f infra/compose/compose.production.yaml up --build -d --wait

docker volume create sponge-caddy-data
docker volume create sponge-caddy-config
docker run --detach \
  --name sponge-caddy \
  --restart unless-stopped \
  --network host \
  --volume sponge-caddy-data:/data \
  --volume sponge-caddy-config:/config \
  caddy:2-alpine \
  caddy reverse-proxy --from "https://$HOSTNAME_FQDN" --to http://127.0.0.1:8080

curl --fail --show-error --silent \
  --retry 30 --retry-delay 10 --retry-all-errors \
  "https://$HOSTNAME_FQDN/api/v1/ready" \
  > /var/log/sponge-ready.json
