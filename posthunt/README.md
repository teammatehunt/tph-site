### Post-hunt steps

The following README explains how to generate a static version of the NextJS site which can be hosted on Vercel's free tier.

Note these instructions assume your site is hosted on `mypuzzlehunt.com`. Replace
this with your actual hunt domain.

teammate has used these with success, though YMMV.

1. Do a recursive wget against the prod site: `./posthunt/static-wget.sh`
1. Also download `mypuzzlehunt.com/api/server.zip` and add it under the `mypuzzlehunt.com/api` directory.
1. After doing the wget, the JSON that gets used by NextJS lies inside a `<script>` tag with `NEXT_DATA` in it, use a Python script to loop over all files, and extract this JSON. All the responses will have a hunt-wide component and per-puzzle component. Save the hunt-wide JSON once to one file, then save the per-puzzle JSON separately. Characters are escaped differently between JS and Python so the script tries to escape everything the way JS expects things to be escaped: Run `./posthunt/get_json.py` and then move `json_responses` to `client/assets/json_responses`
1. Set `IS_STATIC = true` and `USE_WORKER = true` in `client/next.config.js`.
1. Remove `client/pages/puzzles/[slug].tsx`.
1. Change every use of `getServerSideProps` to `getStaticProps`: `sed 's/export const getServerSideProps/export const getStaticProps/' -i **/*.tsx`
1. Oh and `App.getInitialProps` (in `client/pages/_app.tsx`) should be removed/commented as well, we used this to inject hunt info into every page, but doing so counts as a server dependency, even if the hunt info is static.
1. Dynamic routes like `team/[slug].tsx` must be given a list of all valid `slug` params, otherwise they won't build, generate this in the same Python script that parses the recursive wget output. Do the same thing for puzzle slugs. Uncomment `getStaticPaths` in `client/pages/team/[slug].tsx`, `client/pages/hints/[slug].tsx`, and `client/pages/stats/[slug].tsx`.
1. Running `yarn build` will report which pages still rely on the server, and can be used to check what work is left. **Until all pages are converted to be static, doing `yarn export` will not work.**
1. After all pages are converted, do `yarn export`; this will take the build output and put generated HTML into the `out/` directory. The build is slow but this step is very fast, just a few seconds.
1. Run `./posthunt/clean.py client/out`. Important: make sure file paths are not being changed (eg, by Windows or by Dropbox)
1. Copy backend pages from the wget: `cp -r mypuzzlehunt.com/api mypuzzlehunt.com/huntinfo client/out`
1. Copy the contents of `/static` from the prod server and make it `client/out/static`
1. Copy the contents of `/srv/media` from the prod server and make it `client/out/media`
1. Copy everything from `static_root` (note that `sortable.js` needs to be copied by contents): `cp -rL server/puzzles/static_root/* client/out`
1. Vercel's free tier appears to work for hosting static content, and can be configured with a `vercel.json` file to use clean URLs (aka hits to `foo.html` will redirect to `foo` but will read from `foo.html`): `cp posthunt/vercel.json client/out`

Now `client/out` has the entire static site, which can be hosted on Vercel.

### Vercel / Namecheap (DNS) settings

[this takes care to ensure that old https://mypuzzlehunt.com/* links redirect across HTTPS]

Vercel:

- add the repository (from the mypuzzlehunt-public user) to a new project
- create 20xx.mypuzzlehunt.com as a production domain
- add the mypuzzlehunt.com domain to the 20xx.mypuzzlehunt.com project and have it do a 301 redirect

Namecheap:

- make 20xx.mypuzzlehunt.com use a CNAME to point to the vercel server
- change the mypuzzlehunt.com (`@`) A record address to vercel's IP (76.76.21.21)
