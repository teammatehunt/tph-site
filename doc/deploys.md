# Deploys

This will guide you through how the codebase gets built into a docker image and
deployed to a cloud server.

## Types of Servers

### Prod

The real Hunt site (including the registration site). It connects to an
external mail server and can optionally serve assets through a CDN but is
otherwise entirely encapsulated by a set of Docker containers on a single
machine.

This is the only server hunters should be interacting with.

### Staging

The internal version of the site which shows what the Hunt site would look
like. Nothing is shared with prod, and it can have its own domain and email
addresses and CDN.

It is also easy to add additional Github workflows to deploy to additional
staging servers. By default, a staging server will send email only if its
domain matches the email domain.

Note that teammate deployed staging and branch builds to a server serving
multiple domains with a reverse proxy in front. Remove instances of
`SERVER_HTTP_BIND_PREFIX` if deploying without an additional reverse proxy to
accept traffic on the default ports of 443 and 80.

### Branch

When developing, it is often useful to be able to show others what the effect
of a feature branch is without them having to build the site themselves. We set
up a server (which we call the branch server) which could host multiple
versions of site, one for each of the most recent k branches pushed to.

Due to Mystery Hunt 2023 needing the Django backend to keep large ML models in
RAM, we separated the deploy of the backend from the deploys of the frontends
to make newly deployed branches use a shared backend for Python/Django
requests. (The backend was also used as a reverse proxy to forward frontend
requests to the relevant frontend.)

The branch-backend would be deployed manually every so often, and the frontend
for each branch would get deployed whenever the branch was updated and finished
building.

This was set up so that when a commit was pushed to the branch
`feature/my-awesome-puzzle`, it could be viewed at a url like
`https://feature-my-awesome-puzzle.some-branch-server-domain.com` once built.
(Most changes like puzzle postprods were frontend-only changes and did not need
changes to the backend.)

## Github Actions

We use Github Actions for continuous integration and optionally continuous
deployment (CI/CD). The files in `.github/workflows` are set up to build this
repo and deploy.

- **`build-combined.yml`**: build the combined hunt and registration image
- **`build-posthunt.yml`**: build the posthunt archive image
- **`build-push.yml`**: runs other actions on each push to the repo (build hunt image, deploy to a branch subdomain, run unittests)
- **`build-registration.yml`**: build the registration image
- **`deploy.yml`**: template for deploying a docker image to a server
- **`deploy-branch.yml`**: deploy branch frontend to a subdomain for accessible viewing
- **`deploy-branch-backend.yml`**: deploy shared branch backend
- **`deploy-posthunt-staging.yml`**: deploy the posthunt archive image to the staging server
- **`deploy-prod.yml`**: deploy to the prod server
- **`deploy-registration-prod.yml`**: deploy the registration image only to the prod server
- **`deploy-registration-staging.yml`**: deploy the registration image to the registration staging server
- **`deploy-staging.yml`**: deploy the combined hunt and registration image to the staging server
- **`deploy-testing.yml`**: deploy the hunt image to a secondary staging server
- **`docker-buildx.yml`**: template for different build options
- **`refresh-assets.yml`**: template for pulling assets from Google Drive
- **`refresh-assets-branch.yml`**: Pulls assets from Google Drive to the branch server and restarts the server
- **`refresh-assets-staging.yml`**: Pulls assets from Google Drive to the staging server and restarts the server
- **`unittests.yml`**: run unittests

## Github Actions Secrets

You should set these secrets in Github:

- **`CI_REGISTRY_USER`**: username for your container registry
- **`CI_REGISTRY_PASSWORD`**: password for your container registry
- **`DEPLOY_DRIVE_CREDS_BASE64`**: contents of a Google Drive credentials json, encoded as base64 (RFC 4648, ie using + and /). This gets decoded by the linux program base64.
- **`DEPLOY_DUCKDNS_API_TOKEN`**: Duck DNS gets used to manage the wildcard SSL certificate validation used for deploying each branch to a subdomain. Once the server serving branches has a valid certificate, this doesn't matter. To use this, you will need to set a Duck DNS subdomain to point to your branch server. (Requests for subsubdomains, including \_acme.whatever-subdomain.duckdns.org, will go to the same place.)
- **`DEPLOY_SSH_KEY_BASE64`**: SSH key that has been added to `.ssh/authorized_keys`, encoded as base64. Run `base64 id_ed25519` (or replace `id_ed25519` with your key name).
- **`DEPLOY_SSH_KNOWN_HOSTS`**: contents of known hosts file. Put the output of `ssh-keyscan your.domainname.com 2>/dev/null` here. The domains should match the `DEPLOY_HOST` input for deploy actions (or can be the wildcard `*`). Multiple hosts can be in this variable for multiple servers.
- **`PROD_SMTP_PASSWORD` / `STAGING_SMTP_PASSWORD`**: SMTP password for sending prod emails and staging emails. (They can be the same if you send all emails with the same login.)

In addition, you should set the `CI_REGISTRY` and `CI_REGISTRY_IMAGE` env variables in `.github/workflows/deploy.yml` and the other Github workflow files. (teammate continued to use Gitlab despite migrating everything else to Github because Gitlab has unlimited container registry space.)

## Build Process

The `Dockerfile` has a few arguments for enabling different parts or versions
of the site (eg whether building the main hunt site, the registration site,
both, or combining them for the archives).

For CI/CD builds, the build happens in a [simple
image](https://gitlab.com/teammate/docker-with-buildx) we made which combines
docker with [BuildKit](https://github.com/moby/buildkit). BuildKit has now been
integrated into recent Docker versions, so using a recent docker image of
`docker` may work, though this has not been tested. And the command syntax may
have changed slightly.

For local development, `./initialize_dev` or
`./scripts/initialize_staging_localhost` will use docker-compose to build the
image.

The `Dockerfile` utilizes a multi-stage build to facilitate caching, and the
CI/CD builds output not only the resulting image but also a cache image to the
container registry. This helps subsequent builds to be able to reuse layers,
even when built on a completely different machine. Note that depending on
bandwidth speeds, uploading the deploy image and cache image can take a
significant portion of the build time. With Gitlab, we sometimes saw that
uploading the images took up to half of the time for the build action (the
images are multi-gigabyte). Gitlab's container registry is free but likely has
bandwidth speed limits.

The build has separate stages for installing system packages
including Caddy, installing each of Next.js and Python dependencies,
transpiling and bundling Next.js code, and pulling all the pieces together for
the final image. Except for system packages, there are differences between what
the dev and prod environments need. Additionally, the Next.js prod bundle can
only be built from within the dev environment (but this is handled by the
Dockerfile).

## Deploy Process

The steps for a deploy are in the `.github/workflows/deploy.yml` Github Actions workflow.

1. For protected servers (like prod), ensure that the Action is running for a specific branch (like `main`) or tag (like `latest`).
1. Remove existing files on the server from previous deploys.
1. Copy the relevant files to the server for this deploy.
1. Set environment variables for the deployed container by populating the `.env` file.
1. Run `refresh.sh`, which does the following:
   1. Pull the Docker image for this deploy, which is tagged with the current commit and build type (eg, hunt/registration/combined/posthunt).
   1. Run docker-compose to ensure that the container is running with the new image (along with services like Postgres and Redis).
   1. Run database migrations.
   1. For part of the year, in this step, we would load fixtures from yaml files to populate the database. As Hunt drew close, we stopped loading fixtures automatically and instead used the staging or prod database as the source of truth.
   1. Run Django checks.
1. If this is the branch server, prune old images and containers.
