FROM nikolaik/python-nodejs:python3.12-nodejs21 as base

RUN apt-get update && apt-get install --no-install-recommends -y optipng

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR 1

RUN pip install pre-commit==3.6.2

ENV PRE_COMMIT_HOME /pre-commit-cache
