# Files

## Docker compose files

### Deployed docker compose configurations

These files get copied to the various servers by Github Actions.

- **`docker-compose.registry.yml`**: docker compose file for most deploys (prod, staging)
- **`docker-compose.branch.backend.yml`**: for running the shared Django backend for branch deploys
- **`docker-compose.branch.yml`**: for running the frontend for a single branch deploy
- **`docker-compose.unittests.yml`**: run unittest in CI/CD

### Local docker compose configurations

These files combine to start different configurations for
`scripts/initialize_dev` and `scripts/initialize_staging_localhost`. You
shouldn't need to run `docker-compose` directly.

- **`docker-compose.dev.yml`**: start the dev environment
- **`docker-compose.staging.localhost.yml`**: start the staging environment locally
- **`docker-compose.registration.yml`**: add-on to enable the registration site locally
- **`docker-compose.posthunt.yml`**: add-on to enable the posthunt archive site locally
- **`docker-compose.dev.full.yml`**: add-on to enable python dependencies with the `full` label (via Poetry). (This is always enabled in staging.)
- **`docker-compose.env.yml`**: add-on to load environment variables from a `.env` file
- **`docker-compose.force-dev.yml`**: add-on to force the environment to be `dev` (`docker-compose.posthunt.yml` sets to the `posthunt` staging/prod environment by default)

## Other files

- **`Caddyfile.dev`**: reverse proxy configuration used in dev
- **`Caddyfile.prod`**: reverse proxy configuration used in prod/staging
- **`*.gitlab-ci.yml`**: Gitlab CI/CD files (deprecated / not currently functioning)
- **`entrypoint.sh`**: script that the docker container will run on startup
- **`hash_encrypted_filenames.py`**: script the Dockerfile uses in prod/staging to hash the filenames of Next.js files under `client/encrypted` so that they don't leak info
- **`postgresql.default.conf`**: postgres configuration used in dev and staging (no changes from the postgres default)
- **`postgresql.prod.conf`**: postgres configuration used in prod (all customizations are at the end)
- **`prune_test_frontends`**: script to remove old branch containers and images (for a server serving versions of the site for a bunch of branches)
- **`refresh.sh`**: script to start the docker container according to the configuration set for the deploy (last step of the Github deploy action)
- **`supervisord.base.conf`**: portion of supervisord configuration shared between the prod and dev environments
- **`supervisord.dev.conf`**: portion of supervisord configuration for just dev
- **`supervisord.prod.conf`**: portion of supervisord configuration for just prod
