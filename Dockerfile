# syntax=docker/dockerfile:1.4
# base contains system packages
FROM nikolaik/python-nodejs:python3.12-nodejs21 as base

RUN apt-get update && apt-get install --no-install-recommends -y \
	brotli \
	curl \
	git \
	libpq-dev \
	supervisor

ENV POETRY_VERSION 1.8.1
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR 1
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
# yarn --modules-folder has a bug for .bin so add to the path manually
ENV PATH "${PATH}:/node_modules/.bin"
# activate venv
ENV PATH "/.venv/bin:${PATH}"

# install poetry to system python
RUN pip install "poetry==${POETRY_VERSION}"

# build caddy
FROM caddy:2.7.6-builder-alpine as caddy_builder
ENV CADDY_VERSION 6d9a83376b5e19b3c0368541ee46044ab284038b
RUN xcaddy build --with github.com/caddy-dns/duckdns@77870e12bac552ceb76917d82ced6db84b958c1f

# generate python virtual environment
FROM base as python_env
# install all dependencies to a virtual env
RUN python -m venv /.venv
COPY server/poetry/pyproject.toml server/poetry/poetry.lock ./
RUN poetry lock --no-update
RUN poetry install --no-interaction --no-cache --no-root --without dev

# add dev dependencies to virtual environment
FROM python_env as python_env_dev
ARG FULL_PYTHON
RUN poetry install --no-interaction --no-cache --no-root ${FULL_PYTHON:+--extras full}

# node_modules for dev and next build
FROM base as node_modules_dev
COPY client/package.json client/yarn.lock ./
# no --ignore-optional so we get SWC compilation
RUN yarn install --non-interactive

# settings for dev and prod
FROM base as output_base
COPY --link --from=caddy_builder /usr/bin/caddy /usr/bin/caddy
COPY --link --from=scratch / /run/celery
COPY --link deploy/entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]

# collect everything for dev
FROM output_base as output_dev
COPY --link --from=python_env_dev /.venv /.venv
COPY --link --from=node_modules_dev /node_modules /node_modules

# dev environment does not run past this stage

# add full dependencies to virtual environment
FROM python_env as python_env_prod
RUN poetry install --no-interaction --no-cache --no-root --without dev --extras full

# node_modules for prod
FROM base as node_modules_prod
COPY client/package.json client/yarn.lock ./
RUN yarn install --non-interactive --ignore-optional --production --frozen-lockfile

# build .next, need dev yarn environment to build
FROM node_modules_dev as next_prebuild
COPY --link client /app/client
COPY --link client/.docker.yarnrc /app/client/.yarnrc
COPY --link reg-client /app/reg-client
COPY --link posthunt-client /app/posthunt-client
# make ENABLE_POSTHUNT_SITE available to all builds
ARG ENABLE_POSTHUNT_SITE
ENV ENABLE_POSTHUNT_SITE=${ENABLE_POSTHUNT_SITE:-0}

FROM next_prebuild as next_build_client
ARG ENABLE_HUNT_SITE
ENV ENABLE_HUNT_SITE=${ENABLE_HUNT_SITE:-0}
COPY --link deploy/hash_encrypted_filenames.py /hash_encrypted_filenames.py
# rename encrypted files, build hunt site, patch webpack-runtime, and remove build cache
RUN cd /app/client && mkdir -p .next && if [ "$ENABLE_HUNT_SITE" -gt 0 ]; then python3 /hash_encrypted_filenames.py encrypted && yarn build; fi

FROM next_prebuild as next_build_reg_client
ARG ENABLE_REGISTRATION_SITE
ENV ENABLE_REGISTRATION_SITE=${ENABLE_REGISTRATION_SITE:-0}
# build hunt site, patch webpack-runtime, and remove build cache
RUN cd /app/reg-client && mkdir -p .next && if [ "$ENABLE_REGISTRATION_SITE" -gt 0 ]; then yarn build; fi

FROM next_prebuild as next_build_posthunt_client
# build hunt site, patch webpack-runtime, and remove build cache
RUN cd /app/posthunt-client && mkdir -p .next && if [ "$ENABLE_POSTHUNT_SITE" -gt 0 ]; then yarn build; fi

# assert we are building something
FROM next_prebuild
ARG ENABLE_HUNT_SITE
ENV ENABLE_HUNT_SITE=${ENABLE_HUNT_SITE:-0}
ARG ENABLE_REGISTRATION_SITE
ENV ENABLE_REGISTRATION_SITE=${ENABLE_REGISTRATION_SITE:-0}
RUN [ "$ENABLE_HUNT_SITE" -gt 0 ] || [ "$ENABLE_REGISTRATION_SITE" -gt 0 ] || [ "$ENABLE_POSTHUNT_SITE" -gt 0 ]

# collect everything for prod
FROM output_base as output_prod
COPY --link --from=python_env_prod /.venv /.venv

COPY --link server /app/server
RUN cd /app/server && SERVER_ENVIRONMENT=prod ./manage.py collectstatic --noinput
RUN <<EOF
	mkdir -p /static/hunt
	ln -sT /app/client/.next /static/hunt/_next
	ln -sT /django_static /static/hunt/static
	ln -s -t /static/hunt/ /app/server/puzzles/static_root/hunt/*
	mkdir -p /static/registration
	ln -sT /app/reg-client/.next /static/registration/_next
	ln -sT /django_static /static/registration/static
	ln -s -t /static/registration/ /app/server/puzzles/static_root/registration/*
	mkdir -p /static/posthunt
	ln -sT /app/posthunt-client/.next /static/posthunt/_next
	ln -sT /django_static /static/posthunt/static
	ln -s -t /static/posthunt/ /app/server/puzzles/static_root/posthunt/*
EOF

ARG ENABLE_HUNT_SITE
ENV ENABLE_HUNT_SITE=${ENABLE_HUNT_SITE:-0}
ARG ENABLE_REGISTRATION_SITE
ENV ENABLE_REGISTRATION_SITE=${ENABLE_REGISTRATION_SITE:-0}
ARG ENABLE_POSTHUNT_SITE
ENV ENABLE_POSTHUNT_SITE=${ENABLE_POSTHUNT_SITE:-0}

COPY --link --from=node_modules_prod /node_modules /node_modules
COPY --link deploy/Caddyfile.prod /Caddyfile
COPY --link deploy/supervisord.base.conf /etc/supervisord.base.conf
COPY --link deploy/supervisord.prod.conf /etc/supervisord.conf

COPY --link --from=next_build_client /app/client /app/client
COPY --link --from=next_build_reg_client /app/reg-client /app/reg-client
COPY --link --from=next_build_posthunt_client /app/posthunt-client /app/posthunt-client
