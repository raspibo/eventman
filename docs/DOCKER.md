# Docker container

EventMan(ager) requires MongoDB to run.

You can run docker-compose.yml to have a complete environment.

The data is stored in the *eventman_data* volume: do not cancel it.

In the *docker-tools* directory there is a set of tools to build and run another container to dump and restore the database; from that directory you can:

* **dump.sh**: dump the current database in a file like *eventman-dump-2017-11-28T21:57:43.tgz*
* **restore.sh** *eventman-dump-2017-11-28T21:57:43.tgz*: restore the given dump. Notice that the current database is completely removed, so DO NOT restore a dump if you don't have a backup of the current data

