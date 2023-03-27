# TODO

When getting started, be sure to do a search for all FIXMEs and replace them with
appropriate values for your own hunt.

There are also many instances of `teammatehunt.com` and `mypuzzlehunt.com` that
should be replaced.

## Future Improvements

There’s a lot of additional improvements to be made. Here are some of the issues
we’d love to improve if we had more time:

- **Improvements to hint infrastructure.**

  - Fetch and display attachments in emails (these are currently not visible).
  - Hint alerts for stale hints (unanswered after X time)

- **Support for Contact HQ.**

  - In MH 2023, we hacked together this feature by creating a custom "hint" type
    for Contact HQ. However, this feature should have first-class support and
    integration with spoilr.

- **Cleaning up views and templatetags.**

  - Backend endpoints are not well-organized and scattered haphazardly across the
    `server/puzzles/views` directory. It would be great to split these into different
    files like `admin.py`, `stats.py`, etc.
  - There are a lot of templatetags written for Django templates but currently unused.
    These can be removed.
  - A number of endpoints are split or duplicated between tph-site and spoilr.
    In particular, we wrote much of the submission code from scratch due to the
    custom logic we needed for certain rounds in MH 2023. It would be great to
    reintegrate this logic into spoilr.

- **Testing.**

  - We’d love to add more unit test infrastructure for some of the more complex
    logic, such as deep computation or websocket integration.

- **Merging improvements from/to gph-site.**
  - This repo was forked from gph-site and only contains features up to Jul 27, 2021.
    Notably, it is missing all improvements introduced in GPH 2020, and many of
    our backend models have diverged slightly. We’d love to find a process to keep
    the two backends closer in sync, so that teams can choose whichever frontend
    they’re most comfortable with.
  - Some features that are missing from gph-site (as of Feb 2022) include:
    - Surveys
    - One-hint-at-a-time
    - Superuser shortcuts
    - Unit tests

While we welcome pull requests, this repo is not maintained and will be kept up-to-date
with our private teammate repos as a best-effort.
