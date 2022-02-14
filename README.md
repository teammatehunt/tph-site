# Teammate Hunt Template (tph-site)

[[_TOC_]]

## Overview

The teammate repo is based on a fork of [gph-site](https://github.com/galacticpuzzlehunt/gph-site),
with many changes made to support the needs of past Teammate Hunts. The largest change
is changing the site from pure Django to a Next.js + Django hybrid, with a [React](https://web.dev/react/)-based
frontend. As such, it is largely incompatible with gph-site architecture and
unfortunately cannot be merged upstream.

If you are not familiar with React, we suggest using gph-site to get started.
However, if you would like more control over your frontend, especially around
interactive components, this repo is for you.

For setup and development instructions, read on.

For detailed overviews of the backend and frontend, check the READMEs in `server/`
and `client/` respectively.

For a high-level overview of how this repo works, or more advanced features,
check the READMEs in `doc/`.

### How to fork this repo

You can [fork this repo on GitLab](https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html)
directly from the UI, or [fork to GitHub (see Stack Overflow answer)](https://stackoverflow.com/a/22266000).

## System Requirements

Developing in the repository requires `git`, `docker`, and `docker-compose`.

### Mac

- `git`: Install as part of [Xcode](https://developer.apple.com/xcode/) or can be
  installed with `brew install git` if you have [homebrew](https://brew.sh/).
- `docker`: Install [Docker Desktop for
  Mac](https://docs.docker.com/desktop/mac/install/)
- `docker-compose`: Comes with Docker Desktop for Mac

### Windows 10

If your Windows is relatively up-to-date, the easiest way to develop on windows
is via the Windows Subsystem for Linux (WSL).

- WSL: In command prompt or powershell, run `wsl --install` if supported or
  else follow the [Microsoft
  documentation](https://docs.microsoft.com/en-us/windows/wsl/install-win10)).
  - This should work with any selection of linux distro, but Ubuntu is known to
    work.
- `git`: Comes pre-installed with Ubuntu
- `docker`: Install [Docker Desktop for
  Windows](https://docs.docker.com/desktop/windows/install/)
- `docker-compose`: Comes with Docker Desktop for Windows

For all the command in the rest of this readme, use the WSL or Ubuntu terminal.

If you don't want to or can't install these, an alternative is to start a
Ubuntu virtual machine and follow the linux instructions.

### Linux

- `git`: Use your package manager to install `git`
- `docker`: Use your package manager (`apt-get install docker.io` on Ubuntu) or
  follow one of the [official installation
  methods](https://docs.docker.com/engine/install/)
  - It is recommended to add yourself to the docker
    group (`sudo usermod -aG docker $USER` and then log out and log back
    in) so you can run without needing `sudo`.
- `docker-compose`: Depending on your installation source, `docker` may have
  come with `docker-compose`. (Test with `docker-compose --version`.) If not,
  if you have `python` and `pip`, the easiest way to install is with `pip install --user docker-compose`. Otherwise, follow one of [these
  methods](https://docs.docker.com/compose/install/).

## Getting Started

### Set up and start everything

```
./initialize_dev
```

Open a browser and go to `https://localhost:8081/`. There will probably be a
"Not Secure" / certificates warning (because running locally uses a self-signed
certificate). Proceed anyways (in Chrome, click "Advanced" and then "Proceed
anyway (unsafe)").

You should now see a development version of the site! In the dev environment, a
testsolving team has been created with username `dev` and password `dev`. If
you need to access the admin panel, there is also an admin account with
username `admin` and password `admin`.

### Monitor logs

```
./scripts/tail_tph_logs
```

### Stop the server

```
./teardown
```

You can also display docker level logs with `./scripts/tail_docker_logs` but it
is less likely you will need them.

While running, persistent server data is mounted under a docker volume (on
linux it is probably `/var/lib/docker/volumes/{repo_name}_srv_dev`).

## Postprodding Puzzles

To scaffold a new puzzle, run this script and follow the command line prompts
to enter the puzzle title, answer, etc. This will automatically create the
puzzle in the database and the proper frontend files.

```
./scripts/create_new_puzzle
```

Edit `client/pages/puzzles/[INSERT_SLUG].tsx` to your liking. You can
login (username `dev`, password `dev`) and see your puzzle at
`https://localhost:8081/puzzles/[INSERT_SLUG]`. (Static information can be viewed in
the development environment without logging in, but login is needed to
authenticate puzzle data from the server side.)

If you need to edit server side puzzle model information, you can go to
`https://localhost:8081/admin` (username `admin`, password `admin`).

## Style

We use the [black](https://black.readthedocs.io/en/stable/) Python formatter and
[prettier](https://prettier.io/) for Typescript files.

This script will format all code for consistency.

```
./scripts/reformat
```

This is enforced by a [pre-commit check](https://pre-commit.com/), which you can
install with

```
# pip
pip install pre-commit
# or Mac OS
brew install pre-commit

pre-commit install
```

## Sample Postprod Workflow

Changes to the site are version controlled by git. We use merge requests (MRs/PRs)
to review the changes before they are merged into the production branch. Here is
a sample workflow we used to add changes to the site.

- Make sure you have added the puzzle to the fixtures. Either add it via
  `https://localhost:8081/admin` and then run `./scripts/save_fixtures` OR
  edit `server/fixtures/puzzles/<slug>.yaml` directly.
  - Set the puzzle name, slug, and emoji. DEEP threshold can be 0 and answer
    can be `REDACTED` until the full hunt testsolve.
  - If the puzzle has already been testsolved, you can set the `meta` and `round`
    fields accordingly.
- Format, commit, and push changes to GitLab or GitHub.

```sh
./scripts/reformat                         # Format all code (dev server must be running)
git checkout -b postprod/[INSERT_SLUG]     # postprodding should be done on a new branch
git add :/                                 # add all changes to the staging index
git commit -m '[INSERT POSTPROD MESSAGE]'  # commit changes
git push -u origin postprod/[INSERT_SLUG]  # push branch to remote repo (might ask you to authenticate)
```

- Then if you go to your repo on GitLab or GitHub, you will be able to create an MR with your changes.
  - When the MR is created, a pipeline will start which verifies type checks
    and static code generation for typescript/React.
  - If it fails, you can make changes to fix it and push again. If you want to
    run the full build locally, read ["Running as in prod"](#running-as-in-prod).

## Deployment

Build and push steps are configured via GitLab's CI/CD pipeline in
`.gitlab-ci.yml`. Build and tests will automatically run on every commit; you
can manually trigger the tag, publish, and deploy steps via GitLab UI in order
to deploy to staging or production.

You will need to modify the variables for which host to deploy to, as well as
set a few variables in GitLab UI (see the comments in `.gitlab-ci.yml`).

If you would like to switch to GitHub, you'll likely need to rewrite this file
in the format of [GitHub Actions](https://github.com/features/actions).

## Running as in prod

The development environment is built to allow for hot reloading of typescript
and python files. There are occasionally subtle differences between how a
puzzle could operate in the development environment and in staging/production.
The other reason you could be interested in building the prod version is that
Next.js will compile the typescript files with strict type checks.

This will build and start the staging site environment (except with the domain
pointing to localhost). Note that this will use a separate database from the
dev environment.

```
./scripts/initialize_staging --localhost
```

No users or teams are created by default for the staging environment.

## Adding or updating packages

### Python

Editing `server/requirements.txt` and rebuilding the docker container should
work smoothly.

### Typescript

This will require `yarn` on your host system. In `client/` run `yarn install`
and the rebuilding the docker container should work. Running `yarn` on the host
is necessary to update the `yarn.lock` file which contains versions of all
installed packages.

## Dumping the database

To dump the database, run:

```
docker-compose exec -T -u postgres db pg_dump postgres > ~/staging-{date}.dump
```

To load the database (after putting the file on another machine), shut down the
existing containers, delete the `tph_pgdata` volume, start the postgres server,
load the database, and refresh the container.

```
./scripts/teardown.sh
docker volume rm tph_pgdata
docker-compose up -d db
docker-compose exec -T -u postgres db psql postgres < ~/staging-{date}.dump
./refresh.sh
```

# Old Setup

This section is outdated. Docker handles all of these together. But if you're
interested in the components that work together, you can read on.

### Client

The front-end is a full web application written in React, with the Next.js
framework. Run `yarn start` to start the development server. It will
automatically re-build any changes you make to the code.

### Server

The back-end is a Django application that primarily serves as an API to power
the front-end. Run `./manage.py runserver` to start the development server. It
will automatically re-build any changes you make to the code.

### Reverse Proxy

Some requests should go to the front-end's development server, and some to the
back-end's. To route the requests appropriately, we're using `caddy` as a
reverse proxy. Run `sudo ./caddy start` to start it. It needs root permissions
to install an SSL certificate for `localhost` to your system. Even then, you may
need to bypass SSL warnings in your browser.
