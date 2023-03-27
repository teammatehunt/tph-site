FROM nikolaik/python-nodejs:python3.9-nodejs16@sha256:e858a798bf7ec2f4174e7ff756e6c83eb123b687e451a9bf8aced59fa9d2be75 as base

RUN apt-get update && apt-get install --no-install-recommends -y optipng

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR 1

RUN pip install pre-commit==2.19.0

ENV PRE_COMMIT_HOME /pre-commit-cache
