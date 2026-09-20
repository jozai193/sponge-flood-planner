#!/bin/sh
set -eu

mkdir -p "${SPONGE_STORAGE_ROOT}/bundles"
if [ -d /app/seed/bundles ]; then
  cp -R -n /app/seed/bundles/. "${SPONGE_STORAGE_ROOT}/bundles/"
fi

exec "$@"
