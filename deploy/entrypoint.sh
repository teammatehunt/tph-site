#!/bin/bash

# serving directory; persistent dir for db, logs, and media files
mkdir -p /srv/logs
mkdir -p /srv/data
mkdir -p /srv/media
mkdir -p /srv/uploads
mkdir -p /srv/config/pgbouncer

# exec into supervisord, replacing this process and passing all signals
if [ -z "$DONT_RUN_SERVER" ]; then
  exec supervisord --nodaemon --configuration /etc/supervisord.conf
fi
