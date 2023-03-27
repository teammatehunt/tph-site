# Features

Some new features since we forked from gph-site include:

- **NextJS + React powered frontend**, with built-in support for interactive components.
  NextJS comes with a myriad of features, including automatic page routing, client-side
  navigation, and optimized images.

  - On top of that, we built our own components and hooks for working with websockets,
    localStorage, puzzle icons, story notifications, and copy-to-clipboard.

- **Hint threading & email management via admin.**

  - Teams can reply to hint responses and ask for clarification (through email or the site).
    This automatically creates hint threads in the admin page.
  - Emails will show up on an Email page and have the same features as hints
    (claiming, threading, and responding on the site).
  - Users can opt-out / unsubscribe from emails directly on the site.

- **Semi-automatic static site generation.** We’re still working on improving the process,
  but convert your dynamic site to a static site (powered by Pyodide and IndexedDB)
  to save on server costs post-hunt by running Python server code in-browser!

- **Dockerized environments.** Dev, staging, and production all use docker for consistent environments.

While much of the React logic is incompatible with gph-site, we would love your help
in porting some of the backend / Django features there.

For more features added for MH 2023, see [mystery_hunt.md](/doc/mystery_hunt.md)
