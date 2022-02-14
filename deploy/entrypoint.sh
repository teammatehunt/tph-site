#!/bin/bash

# serving directory; persistent dir for db, logs, and media files
mkdir -p /srv/logs
mkdir -p /srv/data
mkdir -p /srv/media
mkdir -p /srv/config/pgbouncer

supervisord --nodaemon --configuration /etc/supervisord.conf
