#!/bin/sh

docker build -t eventman-dump-and-restore .
docker run --name eventman-restore --rm --network="eventman_default" -v `pwd`:/data --link=eventman_eventman-mongo_1:eventman-mongo eventman-dump-and-restore --restore "$1"
