#!/bin/sh
set -eu
umask 077
dest=/opt/backups/kaneo
mkdir -p "$dest"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker exec kaneo-global-postgres-1 pg_dump -U kaneo -d kaneo -Fc > "$dest/$stamp.dump.tmp"
test -s "$dest/$stamp.dump.tmp"
mv "$dest/$stamp.dump.tmp" "$dest/$stamp.dump"
tar -czf "$dest/$stamp-config-runtime.tar.gz" -C /opt configs/kaneo data/kaneo/runtime
find "$dest" -maxdepth 1 -type f \( -name '20*T*Z.dump' -o -name '20*T*Z-config-runtime.tar.gz' \) -mtime +14 -delete
echo "Backup ready: $stamp"
