#!/usr/bin/env bash
set -e

# Ensure the password file is set.
# This is needed for automated authentication.
echo tunnel:1234:*:${POSTGRES_USER}:${POSTGRES_PASSWORD} > ~/.pgpass
chmod 600 ~/.pgpass

# initialize the replica
if [ -f "${PGDATA}/standby.signal" ]; then
    >&2 echo "Found pre-existing replica initialization"
else
    >&2 echo "Initializing replica; pulling data from primary"
    PGPASSFILE=~/.pgpass pg_basebackup -h ${TUNNEL} -p ${TUNNEL_PORT} -U ${POSTGRES_USER} -D ${PGDATA} -R
fi

# start the normal postgres entrypoint
/docker-entrypoint.sh postgres
