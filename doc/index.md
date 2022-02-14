# Documentation

This aims to describe various parts of the teammate site and repo. It is likely
not a comprehensive resource, but aims to describe things well enough to get you
started on how to modify the code to do what you want. See Next.js, Django, and Caddy
documentation for further pointers.

[[_TOC_]]

## Site Overview

The teammate repo is based on a fork of [gph-site](https://github.com/galacticpuzzlehunt/gph-site),
with many changes made to support the needs of past Teammate Hunts. The largest change
is changing the site from pure Django to a Next.js + Django hybrid, with a [React](https://web.dev/react/)-based
frontend.

If you're familiar with gph-site, the code should be somewhat familiar, yet slightly
different from what you may be used to. If you aren't familiar with gph-site, that's okay!
It should make sense with time.

## Life of a Request

Someone tries to visit a page on the teammate site. What happens?

### Step 1: Caddy

The client request first hits [Caddy](https://caddyserver.com/), which we use as a reverse proxy.
Caddy is configured by the Caddyfile, which lives in the `deploy/` directory. There are different
Caddyfiles for dev vs prod. The two are mostly the same, except that dev disables some auth checks
to help debugging.

Depending on the Caddyfile, the request is either:

- Routed directly to Next.js, for pages that are public to everyone.
- Routed directly to Django, for admin pages or API requests against the backend.
- Routed to an authentication check in Django, to decide whether to allow access or not.

Requests go to Next.js by default. URLs that match the patterns in `@needs_check` go to the authentication check.
URLs that match `@django_admin` or `@django` are routed to Django directly.
Admin pages don't have
to live in Django, but the ones we use are based on ones in gph-site, and no one's
felt the need to reimplement them in React.

### Step 2: Django auth check

The Django auth code lives in the `check_access_allowed` function, at `server/puzzles/views/auth.py`.
This slightly messy function determines whether the request should see the originally requested page, or
a 404 error.

Custom puzzle endpoints may need to modify this function, depending on implementation.

### Step 3a: Django endpoints

If the request is routed to Django, it is matched against the urlpatterns in `server/tph/urls.py` to
decide what Django view function to use. By convention, almost all Django URLs start with `api/`
or `internal/`. This convention lets us easily define the patterns in the Caddyfile.

Code in the Next.js will often make a `clientFetch` or `serverFetch` call to the Django backend. These
calls always prepend `api/` to the URL for convenience.

If you've worked with gph-site before, many puzzle endpoints that normally returned `HttpResponse`
objects now return `JsonResponse` objects instead, and instead of rendering them in HTML templates, they
are rendered via React code in the `client/` folder.

### Step 3b: Next.js endpoints

URLs for the Next.js endpoints are decided based on the directory structure of the `client/` subfolder.
For example, a request to `mypuzzlehunt.com/a/b` would go to `client/pages/a/b.tsx`.

Many pages in the site define a `setServerSideProps` function. This is a dedicated function in Next.js
to do server-side processing before the user sees the content. Often this function will do a
`serverFetch` call against the Django backend to populate the props before they get used by frontend
code.

Some Next.js pages have brackets in their name, i.e. `[slug].tsx`. This is the syntax for
[dynamic routes](https://nextjs.org/docs/routing/dynamic-routes), which let us pass arguments from the URL
into the params.

## Discord Alerts

Almost all Discord alerts from the site are based on Discord webhooks. Every Discord server lets you create
webhooks, and sending a POST request to the generated URL lets any user post a message in the channel
(whether they are authenticated or not).

This is good for basic alerts, but its chief limitation is that you can only send text content, and cannot
edit previously made messages. More complex behaviors requiring running the Discord bot,
whose code is at `server/discord_bot.py`. Despite living in `server/`, it's not run by Django, the
deploy starts it separately. Currently we use the bot to manage hints and email. New hints trigger an
alert, and the hint response is edited in-line to that alert.

The way the bot works is **very** hacky. Since the bot does not live in Django code, it
doesn't have direct access to the Django database. Instead, whenever we want to trigger a bot action,
the Django server hits a webhook with a special message. The Discord bot monitors the teammate
Discord for these special messages and triggers the appropriate behavior. This was the quick
fix we found that didn't require modifying gph-site code. There's probably a better option, but
it's been okay so far...

By default, only one instance of the bot should ever be running, because parts of the bot are not
idempotent. The deploy script is setup to only run it in prod, not staging or dev. However, you're
welcome to run the bot in dev when implementing new features. Just run `python discord_bot.py` in
a separate terminal (requires installing [discord.py](https://discordpy.readthedocs.io/en/stable/) first.

Known issues:

- If the prod server goes down in the middle of replying to a hint, the bot will lose track of what
  message to edit.
- If a new hint is made in the staging or dev server, it's possible for the bot to get confused about
  what message goes to what hint (we assume primary key is unique but primary keys can overlap between
  prod site and staging site)

## Custom puzzle endpoints

Sometimes, puzzles might have special requests that should be guarded behind server-side calls
(for example, an input box separate from the answer checker). To configure these, you can define
`PUZZLE_SPECIFIC_ENDPOINTS` in `server/tph/urls.py`, a mapping from puzzle slug to a list of
endpoints. Each endpoint should return a JsonResponse for the client to parse.

You can make a call to this endpoint using `clientFetch` in JS.

## Interactive Components

So you want to build an interactive component (e.g. puzzle state that syncs automatically between
teammates, puzzle solved alerts, or a "teamwork time" game)! How does this work?

The client starts by initiating a websocket request in JS: a long-lived connection that remains
open as long as interactivity lasts. Data (encoded as bytes) can flow bidirectionally across the
websocket. In Django, this is handled through the [Channels](https://channels.readthedocs.io/en/stable/)
library, which uses Redis to pass messages under the hood.

Each client may have an associated uuid (globally unique identifier), user id (if logged in as a team),
and puzzle id (if at a `puzzle/<slug>` url). These are automatically passed to the server
and used to identify which "consumers" to send messages to (see `ClientConsumer.get_<type>_group`).
This ensures that messages can be filtered based on the logged-in team or even unique user.

In this repo, this is largely abstracted into two points:

- `client/utils/fetch.ts` implements a hook called `useEventWebSocket`. Pass it
  a callback function `onJson` and a `key` (optional, for filtering the type of message)
  and it will call the callback whenever data is sent from the server. See
  `client/pages/internal_frontend/echo_websocket.tsx` for an example.
- `server/puzzles/consumers/__init__.py` has a method `receive_json` where you
  can define `PUZZLE_HANDLERS`. This should be a map from puzzle slug to a handler
  method that takes a User, uuid, and JSON content. If this handler is synchronous
  and accesses the database, you may need to wrap it in `database_sync_to_async`.
- If you wish to send data to the client outside of a puzzle, you can import
  `ClientConsumer` directly and send an event to a group directly.

## Post-hunt Staticification

Django + Next is inherently dynamic and renders a lot of puzzle content server-side.
This is necessary during the hunt (to gate solvers based on hunt progress), but we often
want to maintain a static (HTML + JS-only) version of the site after the hunt is complete
to reduce server costs.

Throughout the client code, we use the `process.env.isStatic` to guard features that
should only appear when the hunt is static, such as a static answer checker (the webpack
compiler optimizes out any dead code when this is turned off, so you don't have to worry
about increased bundle size).

For interactive logic, we use a library called [Pyodide](https://pyodide.org/en/stable/)
which enables us to install and run Python in the browser. This essentially lets us
run server code with minimal changes in the browser! In place of Postgres, IndexedDB
is used as a client-side database.

Read more about how to set this up and deploy in posthunt/README.md.
