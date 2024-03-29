# Teammate Hunt Template (tph-site)

## Overview

The teammate repo is based on a fork of [gph-site](https://github.com/galacticpuzzlehunt/gph-site),
with many changes made to support the needs of past Teammate Hunts. The largest change
is changing the site from pure Django to a Next.js + Django hybrid, with a [React](https://react.dev/)-based
frontend. As such, it is largely incompatible with gph-site architecture and
unfortunately cannot be merged upstream.

If you are not familiar with React, we suggest using gph-site to get started.
However, if you would like more control over your frontend, especially around
interactive components, this repo is for you.

For setup and development instructions, read on.

For detailed overviews of the backend and frontend, check the
[server](server/README.md) and [client](client/README.md) READMEs respectively.

For a high-level overview of how this repo works, or more advanced features,
check the [doc](doc/index.md) directory.

For additional features added for Mystery Hunt 2023, see [Mystery Hunt](doc/mystery_hunt.md).

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

For all the commands in the rest of this readme, use the WSL or Ubuntu terminal.

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

### Clone this repo

Enter your github username and password when prompted.

```
# FIXME
git clone https://github.com/teammatehunt/tph-site.git
cd tph-site
```

If you have ssh keys set up, you can clone with `git clone git@github.com:teammatehunt/tph-site.git` (FIXME)
instead for passwordless authentication.

### Set up and start everything

This will install git pre-commit hooks and build the development environment.

```
./initialize_dev
```

Next, load the fixtures (puzzle, round, and other metadata imported from PuzzUp):

```
./scripts/load_fixtures
```

Open a browser and go to `https://localhost:8081/`. There will probably be a
"Not Secure" / certificates warning (because running locally uses a self-signed
certificate). Proceed anyways (in Chrome, click "Advanced" and then "Proceed
anyway (unsafe)").

You should now see a development version of the site! In the dev environment, a
testsolving team has been created with username `dev` and password `dev`. If
you need to access the admin panel, there is also an admin account with
username `admin` and password `admin`.

If you have multiple domains enabled, you can go to `https://localhost:8082`.

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
linux it is probably `/var/lib/docker/volumes/tph-site_srv_dev`). (FIXME)

## Postprodding Puzzles

Postproduction is integrated with PuzzUp. You can use the autopostprod feature on PuzzUp to scaffold a new puzzle
(see the [Guide here](https://github.com/teammatehunt/puzzup#autopostprod)).

This will automatically create a new branch you can checkout on Git. Make sure to
run `./scripts/load_fixtures` to load the puzzle metadata into your database.

### Manual Scaffolding

To scaffold a puzzle manually, run this script and follow the command line prompts
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
[pre-commit](https://pre-commit.com/) will enforce formatting (as well as run
some other basic checks like ensuring we do not commit directly to staging or
main). This gets installed to your git hooks on the first instantiation of
`./initialize_dev`.

If you have a section of code that you don't want to be touched by our
formatters, you can add a comment to ignore. For example, in `.tsx` files,
inserting `{/* prettier-ignore */}` will cause the entire HTML/JSX node
following the comment to not be reformatted. This can be useful for pasting in
generated code, such as a table produced from an external script (though we
would encourage storing generated data as intermediary json assets and
importing them instead).

If you need to commit and bypass style checks (eg, code is a broken
work-in-progress and you are trying to share with someone), you can run `git commit --no-verify` to not run git hooks.

## Merging Postprodding Changes

Changes to the site are version controlled by git. We use pull requests (PRs)
to review the changes before they are merged into the production branch.

- Make sure you have added the puzzle to the fixtures. Either add it via
  `https://localhost:8081/admin` and then run `./scripts/save_fixtures` OR
  edit `server/tph/fixtures/puzzles/<slug>.yaml` directly.
  - Set the puzzle name, slug, and emoji.
  - If the puzzle has already been testsolved, you can set the `meta` and `round`
    fields accordingly.
- Format, commit, and push changes to Github.

```sh
git checkout -b postprod/[INSERT_SLUG]     # postprodding should be done on a new branch
git add :/                                 # add all changes to the staging index
git commit -m '[INSERT POSTPROD MESSAGE]'  # commit changes
git push -u origin postprod/[INSERT_SLUG]  # push branch to github (might ask you to authenticate)
```

- Then if you go to <FIXME repo url>, you
  will be able to create a PR with your changes.
  - When the PR is created, a pipeline will start which verifies type checks
    and static code generation for typescript/React.
  - If it fails, you can make changes to fix it and push again. If you want to
    run the full build locally, read ["Running as in prod"](#running-as-in-prod).

## Deployment

Build and push steps are configured via Github CI/CD workflows in
`.github/workflows`. Build and tests will automatically run on every commit.
After pushing a commit, the frontend will be deployed to
`[YOUR-BRANCH-SLUG].branch.teammatehunt.com`. The basicauth username / password
are the same as the ones for the staging site.

You can manually trigger the deploy step via the [GitHub Actions
UI](FIXME repo-url /actions/workflows/deploy-staging.yml)
in order to deploy to staging or production (by clicking "Run Workflow"). Note
that deploys to prod will fail if you pick something other than the `main`
branch.

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
./scripts/initialize_staging_localhost
```

No users or teams are created by default for the staging environment.

## Fetching art assets

Google Drive is the source of truth for round art and puzzle icons. We use
`./scripts/sync_media` to sync these to a machine and generate a unique mapping
of hashed filenames to serve from. To fetch these locally, you can put the
[service account credentials FIXME](FIXME)
in the root of this repo and run `./scripts/sync_media [DEST_DIRECTORY]`.
To fetch them into the development container, in the root of this repo run `./scripts/sync_media dev`.

The asset map is loaded into each process' memory during startup automatically.
If you already have a server running, either restart your server or hot reload
Django (by editing/saving a Python file) to see the new assets.
To resolve a path to its hashed name, use `puzzles.assets.get_hashed_url`.

## Adding or updating packages

### Python

After adding a dependency to `server/poetry/pyproject.toml`, running
`./scripts/update_poetry_lock` (while the dev container is running), and
rebuilding the docker container should work smoothly. Also see
[the backend documentation](server/README.md#repository-details).

### Typescript

After adding a dependency to `client/package.json`, running
`./scripts/update_yarn_lock` (while the dev container is running), and
rebuilding the docker container should work smoothly.

## Dumping the database

To dump the database, run:

```
docker-compose exec -T -u postgres db pg_dump postgres > ~/{staging,prod}-{date}.dump
```

To load the database (after putting the file on another machine), shut down the
existing containers, delete the `tph_pgdata` volume, start the postgres server,
load the database, and refresh the container.

```
./teardown
docker volume rm tph_pgdata
docker-compose up -d db
docker-compose exec -T -u postgres db psql postgres < ~/staging-{date}.dump
./initialize_dev
```

## Running the registration site

Use the `--reg` arg (ie, `./initialize_dev --reg` or
`./scripts/initialize_staging_localhost --reg`) to also run the registration site
on `https://localhost:8083`.

The frontend for the registration site uses `reg-client/` instead of `client/`,
though files and directories that should be the same can be symlinked.

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
reverse proxy.
