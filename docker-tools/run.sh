#!/bin/sh

if [ $# -lt 1 ] ; then
	exit 1
fi

cmd="$1"

if [ "${cmd}" = "--dump" ] ; then
	echo "INFO: dumping..."
	mongodump --host mongo --out /tmp/ --db eventman
	cd /tmp
	tar cfz /data/eventman-dump-`date +'%Y-%m-%dT%H:%M:%S'`.tgz eventman
elif [ "${cmd}" = "--restore" ] ; then
	if [ -z "$2" ] ; then
		echo "ERROR: missing argument to --restore"
		exit 2
	fi
	echo "INFO: restoring $2..."
	tar xfz "/data/$2" -C /tmp
	mongorestore --host mongo -d eventman /tmp/eventman
else
	echo "ERROR: command not recognized: use --dump or --restore dumps/file.tgz"
	exit 3
fi

