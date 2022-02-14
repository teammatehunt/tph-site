# TODO

When getting started, be sure to do a search for all FIXMEs and replace them with
appropriate values for your own hunt.

## Future Improvements

There’s a lot of additional improvements to be made. Here are some of the issues we’d love
to improve if we had more time:

- **Improvements to hint infrastructure.**

  - Add support for hint response templates in the database / admin page, and the
    ability to paste them into the hint response.
  - Standardize common hint/email signatures, which could be appended to an email
    from a button on the admin page.
  - Fetch and display attachments in emails (these are currently not visible).
  - Hint alerts for stale hints (unanswered after X time)

- **Better support for generic styling / theming.**

  - We did some work adding CSS variables, but a lot of styles are hard-coded into
    various components. We’d love to clean this up so that it’s easy to style or theme
    a hunt each year without editing individual components.

- **Autogenerating puzzle content.**

  - Today, a lot of puzzle content needs to be manually created in React, which poses a
    higher barrier of entry than gph-site. We’re working on integrations with Palindrome’s
    puzzle-planning tool, PuzzUp, including the ability to automatically generate puzzle
    content in React from Google Docs. This probably won’t be available until after
    Mystery Hunt 2023, but stay tuned!

- **Cleaning up views and templatetags.**

  - Backend endpoints are not well-organized and scattered haphazardly across the
    `server/puzzles/views` directory. It would be great to split these into different
    files like `admin.py`, `stats.py`, etc.
  - There are a lot of templatetags written for Django templates but currently unused.
    These can be removed.

- **Testing.**

  - We’d love to add unit test infrastructure for some of the more complex logic,
    such as deep computation or websocket integration.

- **Cloud hosting / CDN for static resources.**

  - We serve most of our images statically (from Django or NextJS). Unfortunately the
    client-side images are 1) committed into the repo, and 2) processed during build time.
    This is not an issue for smaller / less image-heavy hunts, but we found it to be a pain
    in Teammate Hunt 2021. Hosting our images on S3 or Google Cloud Storage would alleviate
    this problem.

- **Merging improvements from/to gph-site.**
  - This repo was forked from gph-site and only contains features up to Jul 27, 2021.
    Notably, it is missing all improvements introduced in GPH 2020, and many of our backend
    models have diverged slightly. We’d love to find a process to keep the two backends
    closer in sync, so that teams can choose whichever frontend they’re most comfortable with.
  - Some features that are missing from gph-site (as of Feb 2022) include:
    - Surveys
    - One-hint-at-a-time
    - Superuser shortcuts
    - Unit tests

While we welcome pull requests, this repo is not maintained and will be kept up-to-date
with our private teammate repos as a best-effort. (We likely won’t have much time to
merge improvements until after Mystery Hunt 2023.)
