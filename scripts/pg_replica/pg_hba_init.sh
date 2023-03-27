#!/usr/bin/env bash
# this script is called on database initialization and every time the container
# is started
if [ -f "${PGDATA}/pg_hba.conf" ]; then
	# set the contents of pg_hba.conf
	cat <<- EOF > "${PGDATA}/pg_hba.conf"
	# TYPE  DATABASE        USER            ADDRESS                 METHOD

	# "local" is for Unix domain socket connections only
	local   all             all                                     trust
	# IPv4 local connections:
	host    all             all             127.0.0.1/32            trust
	# IPv6 local connections:
	host    all             all             ::1/128                 trust
	# Allow replication connections from localhost, by a user with the
	# replication privilege.
	local   replication     all                                     trust
	host    replication     all             127.0.0.1/32            trust
	host    replication     all             ::1/128                 trust

  # Allow authenticated users to connect from anywhere
	host    all             all             all                     md5
  # Allow authenticated users to perform replication
	host    replication     all             all                     md5
	EOF
fi

# exec into the entrypoint
if [ -n "$1" ] ; then
	exec "$@"
fi
