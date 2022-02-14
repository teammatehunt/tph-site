#!/usr/bin/env bash
set -e
# this script gets copied to project root directory
cd $(dirname $(realpath "${BASH_SOURCE}"))

# docker-compose.registry.yml gets copied to project root directory
docker-compose() {
  command docker-compose -f docker-compose.yml -f docker-compose.registry.yml "$@"
}

docker-compose pull
docker-compose up -d
docker-compose exec -T tph /app/server/manage.py migrate --no-input
# TODO: load fixtures in prod
if grep -q SERVER_ENVIRONMENT=staging .env ; then
  :
  # commands to run in staging only
  #docker-compose exec -T tph /app/server/manage.py loaddata /app/server/fixtures/puzzles.yaml
  #docker-compose exec -T tph /app/server/manage.py loaddata /app/server/fixtures/story.yaml
fi
# docker-compose exec tph /app/server/manage.py ensure_user_created admin --password admin --admin
# TODO: handle creating a superuser
docker-compose exec -T tph /app/server/manage.py check
