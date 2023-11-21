### Post-hunt steps

This README explains how to generate a static version of the NextJS site.

We host Teammate Hunt 2020 and Teammate Hunt 2021 on Vercel's free tier.
Mystery Hunt 2023 timed out during deploys, but this process was used to
generate the static files

teammate has used these with success, though YMMV.

1. Grab a dump of the prod database. This can be done on the prod machine with `docker-compose exec -T -u postgres db pg_dump postgres > ~/prod-{date}.dump`.
1. Dump the prod database into the local database.
   ```sh
   ./teardown # ensure the local container is stopped
   docker volume rm mh-20xx_pgdata # nuke the old database (replace mh-20xx)
   docker-compose -f docker-compose.yml -f deploy/docker-compose.staging.localhost.yml up -d db # start just postgres
   docker-compose exec -T -u postgres db postgres < prod-{date}.dump # load the prod database
   ```
1. Ensure media assets are synced.
   ```sh
   docker run --rm -it -v mh-20xx_srv:/srv -w /srv alpine rm -rf media # clear old media assets (replace mh-20xx)
   ./scripts/sync_media --full mh-20xx_srv # run the script to sync assets from Drive (replace mh-20xx)
   ```
1. Build and start the posthunt version of the site with `./scripts/initialize_staging_localhost --posthunt`.
1. (optional) Apply any fixture database changes between the prod site and the archive. For example, this might include:
   1. Removing any answers/data from the public access team.
   1. Updating puzzle positions.
   ```sh
   docker-compose exec -T tph /app/server/manage.py puzzle_positions --fixtures-dir fixtures
   ```
   1. Any database changes needed for specific puzzles on the static site.
1. Fix all the FIXMEs and then run the export script `./posthunt/export_site.sh`. We suggest your read through the comments of the script to understand what steps might need to be adapted for your hunt.
1. If deploying to Vercel, also copy over the `vercel.json` file. (This is currently commented out in the `export_site.sh`.) This tells Vercel to use clean URLs (aka hits to `foo.html` will redirect to `foo` but will read from `foo.html`).

Now `posthunt/exported_static_site` has the entire static site.

### Vercel / Namecheap (DNS) settings

[this takes care to ensure that old https://teammatehunt.com/* links redirect across HTTPS]

Vercel:

- add the repository (from the teammatehunt-public user) to a new project
- create 20xx.teammatehunt.com as a production domain
- add the teammatehunt.com domain to the 20xx.teammatehunt.com project and have it do a 301 redirect

Namecheap:

- make 20xx.teammatehunt.com use a CNAME to point to the vercel server
- change the teammatehunt.com (`@`) A record address to vercel's IP (76.76.21.21)
