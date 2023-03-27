# Spoilr (HQ)

A Django project to handle hunt-agnostic puzzle management for puzzle hunts such as the MIT Mystery Hunt.

This directory is a copy of the [spoilr-teammate](https://github.com/teammatehunt/spoilr-teammate) repo.

## Features

- Models, API and events system for common hunt behaviour.
- Managing incoming interactions, hint requests, contact requests, and emails.
- General [task management](#tasks) framework for incoming items.
- Progress dashboards.
- Logging system.
- Settings system.
- Lifecycle management.
- Common view decorators.
- User/team authentication and impersonation.

## Design philosophy

It provides a [`core`](spoilr/core/) package with models and APIs common to most hunts. The [`core`](spoilr/core/) package aims to have no dependencies on other spoilr packages, or on code specific to the 2022 hunt.

It also provides a series of plugin apps for features such as email management or progress dashboards. This encapsulation of features into their own Django app is to better organize code, and to make selecting individual features for reuse simpler. Each plugin app is responsible for one feature, and should mostly depend on only `spoilr.core`. However, it may depend on other apps or on 2022-hunt specific code where appropriate, such as a dashboard showing 2022-specific features.

There's also the [`hq`](spoilr/hq/) package. It contains the HQ home page dashboard, some common stylesheets, and some utility views and behaviours such as [task management](#tasks). It also contains some "legacy URLs" that haven't been migrated to the plugin-style architecture yet.

## Tasks

Spoilr surfaces tasks for HQ to act upon so the hunt can proceed. We've defined common models and actions for tasks such as claiming them, snoozing them, and resolving them. These are used throughout other spoilr plugins as appropriate.

## Tick

`do_tick` needs to be scheduled peridically throughout the hunt. Teammate used [celery](https://docs.celeryq.dev/) to visit the endpoint once a second.

## Changes from Prior Iterations

Besides general cleanup, the largest changes made by teammate were an overhaul of the email and hint models to more closely match [tph-site](https://github.com/teammatehunt/tph-site). This significantly increases the complexity of these modules.

## Areas Needing Work

The interactions module is the least polished. It is likely that replies to emails sent from the interaction dashboard will not be threaded properly.

Many locations requiring changes for your hunt and a few that we did not get to are labeled `FIXME(update)`

## Acknowledgements

This is heavily influenced by the [2021 hunt's version of spoilr](https://github.com/YewLabs/silenda/tree/master/spoilr) and the [2022 hunt's version of spoilr](https://github.com/Palindrome-Puzzles/2022-hunt/tree/main/spoilr)
