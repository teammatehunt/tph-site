# teammate hunt client

This is the software that powers the frontend of the teammate hunt website.
Most of the setup and server are handled by Docker, but if you want to run the
frontend separately, you can follow the instructions below.

## Getting Started

Simply install NodeJS and run `yarn` to install the client dependencies.

## Development

Use `yarn start` to start the NextJS server. You'll probably want to spin up
Caddy and Django if you want to serve any server-side content.

The NextJS app is divided into the following directories and files:

- `next.config.js`: The main config file for NextJS, which contains settings
  and custom webpack plugins. This file also contains an allowlist for which
  pages are publicly listed in the manifest (see comments for details).

- `package.json`: Used by webpack, this configures the packages to install as
  dependencies, as well as any scripts that can be run as `yarn <command>`.

- `pages/`: The list of pages rendered on the website. The url reflects the
  directory structure, starting from `teammatehunt.com/`. As suggested by the
  directory name, puzzles go in `pages/puzzles/<slug>` and solutions in
  `pages/solutions/<slug>`. With a bit of Caddy magic, any files inside one of
  these directories will only be accessible if a logged-in team has unlocked
  that puzzle slug.

- `components/`: React components that should be shared across different pages.
  For example, crossword grids, tables, and the copy-to-clipboard functionality
  live here. Note anything here might be publicly visible and inspectable,
  unless its only imports are from behind a puzzle page.

- `encrypted/`: Frontend content that should be encrypted. This is used for content
  that should be hidden, but which would be hard to send from the server. Most
  likely you will not need this, but if you do, see `utils/encrypted`.

- `assets/`: Images, sound files, and other static assets to use on the site.
  Like puzzles, they can be locked behind a puzzle slug. We also have a
  `public/` directory for public images.

- `utils/`: Helper methods for working with various browser features like
  localStorage, keypresses, animations, and more.

## Styling

We use the [Tailwind framework](https://tailwindcss.com/) to style class-based
CSS, as well as CSS variables for theme customization.

For more complex styles, we use [styled components](https://styled-components.com/)
to dynamically render CSS in JS. Typically this can be seen in the `<style jsx>`
tags floating around different React components. In addition, global classes and
styles are defined
in `style.css`.

We've defined many [CSS variables](/client/styles/theme.css) that can be
overwritten by "themes" in [`components/layout.tsx`](/client/components/layout.tsx).
To configure this, you'll want to update the `themeStyle` function based on hunt
progress or user input.

One caveat is that styled components are locally scoped (i.e. they only apply to
the component they are defined in. You can override this by adding a `:global()`
selector, or making the entire style tag `<style jsx global>`. For code quality
reasons, try avoiding globals when possible. The [resolve](https://github.com/vercel/styled-jsx#the-resolve-tag)
tag can be used to define scoped styles.
