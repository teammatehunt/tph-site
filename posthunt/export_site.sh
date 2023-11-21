#!/usr/bin/bash
set -e
REAL_SOURCE="$(perl -e "use Cwd 'abs_path'; print abs_path('${BASH_SOURCE}')")"
cd "$(dirname "${REAL_SOURCE}")"

REPO_NAME=$(basename $(dirname $(pwd)))

# This script exports the site to a static site. The staging posthunt site
# needs to be running on localhost with a copy of the prod database and media
# assets for this to work.

# Working directory is mh-20xx/posthunt

# Shared wget settings -- consider removing --no-verbose when debugging
WGET_SETTINGS=$(echo \
  --no-verbose \
  --force-directories \
  --max-redirect=0 \
  --ignore-tags=img,link,script,style \
  --html-extension \
  --restrict-file-names=windows \
  --retry-on-http-error=500 \
  --tries=3 \
  --domains localhost \
  --no-parent \
  --no-check-certificate \
  --exclude-directories=/20xx/_next,/20xx/media) # FIXME: replace 20xx

# Clear old api json responses
docker-compose exec -T tph rm -rf /srv/json_responses
# Save to mh-20xx/posthunt/site_dump and let Django save api responses
rm -rf site_dump localhost+8084
# FIXME: replace 20xx, domain names, and add any other urls needed to scrape the site
wget --recursive ${WGET_SETTINGS} \
  https://localhost:8084/20xx/mypuzzlehunt.com \
  https://localhost:8084/20xx/registration.mypuzzlehunt.com \
  https://localhost:8084/20xx/mypuzzlehunt.com/puzzles \
  https://localhost:8084/20xx/mypuzzlehunt.com/events \
  https://localhost:8084/20xx/mypuzzlehunt.com/story \
  https://localhost:8084/20xx/mypuzzlehunt.com/api/server.zip \
  https://localhost:8084/20xx/spoilr/progress/solves/ \
  || { >&2 echo "ERROR: wget could not download all pages" && false; }
# Fetch solutions and stats api calls for any puzzles that are only client-side rendered (not server-side rendered)
# FIXME: you can probably remove this command, or else change it to match your hunt
docker-compose exec -T tph find \
  /srv/json_responses/20xx/mypuzzlehunt.com/api/factory/basement \
  /srv/json_responses/20xx/mypuzzlehunt.com/api/factory/factory-floor \
  /srv/json_responses/20xx/mypuzzlehunt.com/api/factory/office \
  -type f \
  | xargs basename -s .json | \
  xargs -I{} wget ${WGET_SETTINGS} \
  https://localhost:8084/20xx/mypuzzlehunt.com/solutions/{} \
  https://localhost:8084/20xx/mypuzzlehunt.com/stats/{} \
  || { >&2 echo "ERROR: wget could not download all factory pages" && false; }
# Fetch story links
# FIXME: replace 20xx and domain
docker-compose exec -T tph \
  grep -P --no-filename --only-matching '(?<="url": ")[^"]*(?=")' \
  /srv/json_responses/20xx/mypuzzlehunt.com/api/story.json \
  | sed 's|^|https://localhost:8084|' \
  | xargs wget ${WGET_SETTINGS} \
  || { >&2 echo "ERROR: wget could not download all story pages" && false; }
mv localhost+8084 site_dump

# Tag container with dev dependencies capable of performing the export
DOCKER_BUILDKIT=1 docker build -t posthunt_builder --target next_prebuild --build-arg ENABLE_POSTHUNT_SITE=1 ..

# Patch the client and perform the export
rm -rf staticfiles_cache exported_static_site
rm -rf build
docker run --rm -i -v "${REPO_NAME}_srv":/srv_staging -v "$(pwd)":/posthunt -e HOST_UID="$(id -u)" posthunt_builder bash <<'EOF'
set -e

set -v # print commands

# patch Next.js render to pass pathname in getStaticProps context
grep 'data = await getStaticProps({' /node_modules/next/dist/server/render.js
sed 's/\(data = await getStaticProps({\)/\1 resolvedUrl: pathname,/' -i /node_modules/next/dist/server/render.js

# replace api json responses
rm -rf /app/client/assets/json_responses /app/reg-client/assets/json_responses
cp -r /srv_staging/json_responses /app/client/assets/json_responses
ln -sT ../../client/assets/json_responses /app/reg-client/assets/json_responses

# ensure IS_STATIC exists and replace its value
grep '^const IS_STATIC = false;' /app/client/next.config.js
sed 's/^const IS_STATIC = false;/const IS_STATIC = true;/' -i /app/client/next.config.js

# convert props
find /app -type f -name '*.tsx' | xargs sed 's/\bgetServerSideProps\b/getStaticProps/' -i
# enable static paths
find /app -type f -name '*.tsx' | xargs sed 's/\bgetStaticPathsInStaticExport\b/getStaticPaths/' -i
# remove everything between STATIC_SITE_REMOVE_START and STATIC_SITE_REMOVE_END
find /app -type f -name '*.tsx' | xargs sed -n '/STATIC_SITE_REMOVE_START/,/STATIC_SITE_REMOVE_END/!p' -i

# remove routes not needed for the static site
rm /app/client/pages/puzzles/[slug].tsx
find /app -regex '.*/pages/\(.*/\)?hints/\[slug\].tsx' | xargs rm
find /app -regex '.*/pages/\(.*/\)?reset_password.tsx' | xargs rm
find /app -regex '.*/pages/\(.*/\)?login.tsx' | xargs rm
find /app -regex '.*/pages/\(.*/\)?logout.tsx' | xargs rm
rm /app/reg-client/pages/register-individual.tsx
rm /app/reg-client/pages/register-team.tsx
rm /app/reg-client/pages/unsubscribe.tsx
rm /app/reg-client/pages/hunt.tsx

# set environment variables for the build
# prod google analytics id
# FIXME: uncomment if using google analytics
# export GOOGLE_ANALYTICS_ID=FIXME

# build the Next.js static frontend for the hunt site
cd /app/posthunt-client
mkdir -p .next
yarn build
yarn export
install -o ${HOST_UID} -g ${HOST_UID} -d /posthunt/build
chown -R ${HOST_UID}:${HOST_UID} out
mv out /posthunt/build/20xx # FIXME: replace 20xx

# build and export the Next.js static frontend for the registration site
cd /app/reg-client
mkdir -p .next
yarn build
yarn export
chown -R ${HOST_UID}:${HOST_UID} out
mv out /posthunt/build/20xx/registration.mypuzzlehunt.com # FIXME: replace 20xx and domain
EOF

# Copy Next.js files
cp -r build exported_static_site

# Copy static files
docker cp "${REPO_NAME}_tph_1":/app/server/puzzles/static_root staticfiles_cache
rm staticfiles_cache/hunt/sorttable.js
docker cp -L "${REPO_NAME}_tph_1":/app/server/puzzles/static_root/hunt/sorttable.js staticfiles_cache/hunt/sorttable.js
docker cp "${REPO_NAME}_tph_1":/django_static staticfiles_cache/django_static
cp -rL staticfiles_cache/posthunt/* exported_static_site/20xx/ # FIXME: replace 20xx
cp -rL staticfiles_cache/hunt/* exported_static_site/20xx/mypuzzlehunt.com/ # FIXME: replace 20xx and domain
cp -rL staticfiles_cache/registration/* exported_static_site/20xx/registration.mypuzzlehunt.com/ # FIXME: replace 20xx and domain
cp -r staticfiles_cache/django_static exported_static_site/20xx/static # FIXME: replace 20xx
ln -sT ../static exported_static_site/20xx/registration.mypuzzlehunt.com/static # FIXME: replace 20xx and domain
rm exported_static_site/20xx/mypuzzlehunt.com/mh20xx_activity_log.csv # FIXME: replace 20xx and domain

# Remove hidden staticfiles map
rm exported_static_site/**/static/staticfiles.json

# Copy media files
docker cp "${REPO_NAME}_tph_1":/srv/media exported_static_site/20xx/media # FIXME: replace 2023
ln -sT ../media exported_static_site/20xx/registration.mypuzzlehunt.com/media # FIXME: replace 2023 and domain

# Copy Django responses
mkdir -p exported_static_site/20xx/mypuzzlehunt.com/api # FIXME: replace 20xx and domain
cp site_dump/20xx/mypuzzlehunt.com/api/server.zip exported_static_site/20xx/mypuzzlehunt.com/api/server.zip # FIXME: replace 20xx and domain
mkdir -p exported_static_site/20xx/spoilr/progress/solves # FIXME: replace 20xx
cp site_dump/20xx/spoilr/progress/solves/index.html exported_static_site/20xx/spoilr/progress/solves/index.html # FIXME: replace 20xx

# Standardize names to remove index.html files
mv exported_static_site/20xx/registration.mypuzzlehunt.com/index.html exported_static_site/20xx/registration.mypuzzlehunt.com.html # FIXME: replace 20xx and domain
mv exported_static_site/20xx/spoilr/progress/solves/index.html exported_static_site/20xx/spoilr/progress/solves.html # FIXME: replace 20xx

# Standardize names to use index.html files
# find \
  # exported_static_site \
  # -type f \
  # \( \
  # -name media -prune \
  # -or -name _next -prune \
  # -or -name static -prune \
  # -or -name pyodide -prune \
  # -or -name '*.html' -not -name index.html -not -name 404.html \
  # \) \
  # | sed 's/.html$//' \
  # | xargs -I{} sh -c 'mkdir -p {} && mv {}.html {}/index.html'

# Copy vercel config (only needed if deploying to vercel)
# cp vercel.json exported_static_site/vercel.json

# Add an example Caddyfile for static file serving
# FIXME: replace 20xx and domain
cat <<'EOF' > exported_static_site/Caddyfile
# This caddyfile can be used to run a file server over HTTP.
# Run with `caddy run` from this directory.
# Or:
# docker run --rm --name mitmh20xx -v "$(pwd):/host:ro" -w /host -p 8080:80 caddy caddy run
# to run with docker on port 8080.
http://

redir / /20xx

try_files {path} {path}.html {path}/index.html
file_server {
  hide /.git
}

handle_errors {
  handle /20xx/registration.mypuzzlehunt.com/* {
    rewrite * /20xx/registration.mypuzzlehunt.com/{err.status_code}.html
    file_server
  }
  handle {
    rewrite * /20xx/{err.status_code}.html
    file_server
  }
}
EOF

# FIXME: replace 20xx
cat <<'EOF' > exported_static_site/.htaccess
# This Apache config can be used to run a file server over HTTP.
# To run with docker on port 8080:
# docker run --rm --name mitmh20xx -v "$(pwd):/usr/local/apache2/htdocs:ro" -p 8080:80 httpd sh -c "sed -i 's|AllowOverride None|AllowOverride all|' /usr/local/apache2/conf/httpd.conf && sed -i 's|#LoadModule rewrite_module|LoadModule rewrite_module|' /usr/local/apache2/conf/httpd.conf && exec httpd-foreground"

DirectorySlash off

RewriteEngine on
RewriteBase /

RedirectMatch 404 ^/\.git
RedirectMatch 404 ^/Caddyfile$
RedirectMatch 302 ^/$ /20xx

RewriteCond %{REQUEST_URI} ^/20xx$
RewriteRule ^(.*)$ $1/index.html [L,QSA]

RewriteCond %{REQUEST_FILENAME}.html -f
RewriteRule ^(.*)$ $1.html [L,QSA]
EOF

>&2 echo "Finished exporting the site!"
