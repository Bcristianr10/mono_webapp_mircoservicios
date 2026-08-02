#!/usr/bin/env bash
# Levanta toda la arquitectura de microservicios de Eduflex en el orden correcto:
# red ADSL -> reverse proxy -> bases de datos -> message broker -> APIs -> BFF/WebApp.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Verificando red ADSL =="
if ! docker network inspect ADSL >/dev/null 2>&1; then
    docker network create --driver bridge ADSL --subnet=172.30.0.0/16
else
    echo "La red ADSL ya existe."
fi

echo "== Levantando reverse_proxy =="
(cd "$ROOT/reverse_proxy" && docker compose up -d)

echo "== Levantando micro_dbs =="
(cd "$ROOT/micro_dbs" && docker compose up -d)

echo "== Levantando message_broker =="
(cd "$ROOT/message_broker" && docker compose up -d)

echo "== Construyendo y levantando micro_webapp (APIs + worker de reportes) =="
(cd "$ROOT/micro_webapp" && docker compose up -d --build)

echo "== Construyendo y levantando micro_bff_app =="
(cd "$ROOT/micro_bff_app" && docker compose up -d --build)

echo "== Listo. Estado de los contenedores: =="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
