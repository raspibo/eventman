# Docker container

EventMan(ager) requires MongoDB to run.

You can use docker-compose.yml to have a complete environment. Run: `docker compose up --build`
Please notice that the *qrcode_reader.py* script is not meant to be run in a Docker container.

The data is stored in the *eventman_data* volume: do not cancel it.

The local *data* directory is mounted in the container: you can modify anything inside of it and changes will be reflected immediately in the running instance.

In the *docker-tools* directory there is a set of tools to build and run another container to dump and restore the database; you need the docker-compose running, to execute them. From that directory you can:

- **dump.sh**: dump the current database in a file like *eventman-dump-2017-11-28T21:57:43.tgz*
- **restore.sh**: *eventman-dump-2017-11-28T21:57:43.tgz*: restore the given dump. Notice that the current database is completely removed, so DO NOT restore a dump if you don't have a backup of the current data
- **shell.sh**: open a shell for the database


The application image installs the core, Eventbrite and printing requirements from
`requirements*.txt` into Python's environment. Build tools remain in a separate
build stage. Scanner requirements are for the host and are not installed in the
image. Only the active frontend is copied.

Fonts are external resources: mount them read-only and set
`EVENTMAN_LABEL_TEXT_FONT` and `EVENTMAN_LABEL_BARCODE_FONT` to their absolute
container paths before using the label-printing trigger. See [DEPENDENCIES.md](DEPENDENCIES.md).

The base image uses Python 3.12 on Debian Bookworm; MongoDB uses the 7.0 image
series. These tags and Python version ranges allow patch updates and are not an
immutable release lock. The old `docker-tools` scripts still assume legacy
Compose container names and the `mongo` shell; review them before use with the
current Compose setup.
