#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import monco

COUNT = ('attended', 'afternoon_attended')
GROUP = ('checked_in_by',)

def info(event):
    tickets = event['tickets']
    total = 0
    data = {}
    for ticket in tickets:
        if ticket.get('cancelled'):
            continue
        for key in COUNT:
            value = ticket.get(key)
            if value:
                data.setdefault(key, 0)
                data[key] += 1
        for key in GROUP:
            value = ticket.get(key)
            if value:
                dbkey = '%s.%s' % (key, value)
                data.setdefault(dbkey, 0)
                data[dbkey] += 1
        total += 1
    print('Total registered: %d' % total)
    for key, value in sorted(data.items()):
        print('%s: %s' % (key, value))
    print('')


def run():
    try:
        db = monco.Monco(dbName='eventman')
        events = db.query('events', {'title': sys.argv[1]})
        info(events[0])
    except:
        print('count.py "title of event"')
        sys.exit(1)

if __name__ == '__main__':
    run()
