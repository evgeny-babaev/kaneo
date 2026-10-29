#!/bin/sh
set -eu
set -a
. /opt/configs/kaneo/production.env
set +a
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_DB:?}"
: "${AUTH_SECRET:?}"
: "${KANEO_CLIENT_URL:?}"
: "${KANEO_IMAGE:?}"
echo "Environment OK"
