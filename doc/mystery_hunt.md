# Documentation

This section describes major differences from the previous version of tph_site.

## Integration with spoilr

We migrated a large number of backend endpoints and database tables to use the
hunt infrastructure of [spoilr](https://github.com/teammatehunt/spoilr-teammate).

The motivation for this migration was to separate generic, hunt-agnostic data
from hunt-specific implementation details. As such, many models and views now
import models from spoilr code.

Internal hunt management tools, including pages such as bigboard, have been
replaced by the spoilr admin frontend.

## Google Drive Sync and Asset Mapping

Our approach for versioning assets relied on keeping the assets themselves in Google Drive and maintaining a map from their filenames to a content hash based filename in memory. Hashed assets were never deleted, so old hashes were stil valid in the case of updates during the hunt.

Programatically syncing assets from a Google Drive folder was done with [rclone](https://rclone.org/).

If you choose to go this route, [create a service account](https://cloud.google.com/iam/docs/service-accounts-create) and give it appropriate access to the Google Drive folders by sharing it with the account. Update [rclone.conf](/scripts/rclone.conf) with appropriate folder IDs. It is suggested to provide the credentials in the repo with only read access.

[sync_media](/scripts/sync_media) is the script that syncs assets and writes a map from filename to its content hash.

We also inserted other functionality like adding glow to solved versions of puzzle icons.

There were 3 tiers of assets to keep the burden on having a development copy of the site up and running low.

Developer use of this process is described in [here](/README.md#fetching-art-assets).

## Story and Dialogue Tree

Interactive team story in MH 2023 involved a large number of changes. While hunt-specific details have mostly been removed, the skeleton code remains for posterity.

Story data is encoded in a "dialogue tree" represented by rows in a CSV. Each row or state is a node in the dialogue tree. Different choices by solvers are edges to other states. The syntax mimics that of [Twine](https://twinery.org/), an interactive tool for crafting stories. See [sample.csv](/server/puzzles/data/story/sample.csv) for an example CSV.

This data is parsed and saved into memory in [story.dialogue_tree](/server/puzzles/story/dialogue_tree.py), and is processed via websocket. See the [consumer code](/server/puzzles/consumers/story.py) and the [frontend component](/client/components/story/dialogue.tsx).

## Copyjack

We integrated the newest version of copyjack from MH 2022 into our React component.
See [copy.tsx](/client/components/copy.tsx) for details.

## Support for multiple domains

MH 2023 necessitated the use of multiple domains (registration, museum, factory).
We set up configuration for managing these in local and production environments.
For more details, see [deploys.md](/doc/deploys.md).

## Client code component encryption

Files under `client/encrypted` contain components which should be inaccessible
initially. All typescript files in this directory will be encrypted in
staging/prod (not dev).

Each file will be encrypted with AES-128 CBC, where the key and IV are halves
of the SHA-256 of the concatenation of that file's basename and an encryption
secret key. This key needs to be computed on server in python with
`puzzles.utils.get_encryption_key` and passed to the client as a `cryptKey`
before the client loads the javascript module. The client code should load the
component with `useDynamicEncrypted` (either in a parent component that only
loads after it should be unlocked or passing in a value for the optional
`enabled` parameter). As long as the client has received the `cryptKey` (eg. in
the fetched puzzle props or in a websocket message), it will be able to decrypt
the javascript module on load.
