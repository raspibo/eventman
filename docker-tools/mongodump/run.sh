#!/bin/sh

mongodump --host mongo --out /tmp/ --db eventman
cd /tmp
tar cfz /data/eventman-dump-`date +'%Y-%m-%dT%H:%M:%S'`.tgz eventman

