# Database replication

This set of docker-compose services allows us to stream database updates to a
replica, which serves as a backup and can be swapped/copied in if we lose the
primary.

To start, make sure you can ssh from the host machine to the machine where the
primary is located. Change the `PRIMARY` in the `docker-compose.yml` to the
login location of the primary, and then run `docker-compose up -d` to start the
replica in the background. That's it!

Note that the container will have access to the host's ssh keys in order to
access the remote machine.

## Recovery

To recover the data from the replica and use it as the primary, we will copy
the docker volume to the primary host. The will likely be copying the
`/var/lib/docker/volumes/pg_replica_pgdata` on the replica to replace
`/var/lib/docker/volumes/tph_pgdata` on the primary. The primary should not be
running during this time. Once copied, remove
`/var/lib/docker/volumes/tph_pgdata/_data/standby.signal`, which postgres uses
to determine whether the database is the primary or a replica.

Alternatively, run
`docker-compose exec -T -u postgres replica pg_dump postgres > {name}-{date}.dump`
on the replica to get a dump. This can be used to recreate
the database on a fresh primary by copying the file and then running
`docker-compose exec -T -u postgres db psql postgres < {name}-{date}.dump`.
