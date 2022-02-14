# base contains system packages
FROM nikolaik/python-nodejs:python3.9-nodejs16@sha256:58645b6a0a98e6001c8ff1191df29433463e3d2bd4d528765ac39720d22336bd as base

RUN apt-get update && apt-get install --no-install-recommends -y \
	curl \
	git \
	libboost-all-dev \
	libnss3-tools \
	libpq-dev \
	supervisor

# install caddy
ENV CADDY_VERSION 2.4.6
RUN wget -qO - "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" | \
	tar --no-same-owner -xz -C /usr/bin \
	&& chmod 0755 /usr/bin/caddy \
	&& /usr/bin/caddy version

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR 1
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
# yarn --modules-folder has a bug for .bin so add to the path manually
ENV PATH "${PATH}:/node_modules/.bin"
# activate venv
ENV PATH "/.venv/bin:${PATH}"

# generate python virtual environment
FROM base as python_env
RUN python -m venv /.venv
COPY server/requirements.txt ./
RUN pip install wheel setuptools
RUN pip install -r requirements.txt

# add dev dependencies to virtual environment
FROM python_env as python_env_dev
COPY server/requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# node_modules for dev and next build
FROM base as node_modules_dev
COPY client/package.json client/yarn.lock ./
RUN yarn install --non-interactive --ignore-optional --frozen-lockfile

# settings for dev and prod
FROM base as output_base
COPY deploy/supervisord.base.conf /etc/
COPY deploy/supervisord.prod.conf /etc/supervisord.conf
RUN ln -s /srv/media /media
COPY deploy/entrypoint.sh /
RUN mkdir -p /run/celery
CMD ["/entrypoint.sh"]

# collect everything for dev
FROM output_base as output_dev
COPY --from=node_modules_dev /node_modules /node_modules
COPY --from=python_env_dev /.venv /.venv

# dev environment does not run past this stage

# node_modules for prod
FROM base as node_modules_prod
COPY client/package.json client/yarn.lock ./
RUN yarn install --non-interactive --ignore-optional --production --frozen-lockfile

# build .next, need dev environment to build
FROM output_dev as next_build
RUN mkdir -p /app
COPY client /app/client
RUN cp -f /app/client/.docker.yarnrc /app/client/.yarnrc
RUN cd /app/client && yarn build

# collect everything for prod
FROM output_base as output_prod
COPY --from=node_modules_prod /node_modules /node_modules
COPY --from=python_env /.venv /.venv

RUN mkdir -p /app
COPY client /app/client
COPY server /app/server
COPY deploy/Caddyfile.prod /Caddyfile
RUN cp -f /app/client/.docker.yarnrc /app/client/.yarnrc

COPY --from=next_build /app/client/.next /app/client/.next
RUN mkdir -p /static
RUN ln -sT /app/client/.next /static/_next
RUN cd /app/server && SERVER_ENVIRONMENT=prod ./manage.py collectstatic --noinput
RUN ln -sT /app/server/static /static/static
RUN ln -s -t /static/ /app/server/puzzles/static_root/*
