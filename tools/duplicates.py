#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import monco


def info(event, key, short=False):
    tickets = event['tickets']
    data = {}
    for ticket in tickets:
        if ticket.get('cancelled'):
            continue
        value = ticket.get(key)
        email = ticket.get('email')
        if not (value and email):
            continue
        data.setdefault(value, []).append(email)
    for key, value in data.items():
        if len(value) < 2:
            continue
        output = '%s (%d persons)' % (key, len(value))
        if not short:
            output += ': %s' % ', '.join(value)
        print(output)
    print('')


def run():
    try:
        db = monco.Monco(dbName='eventman')
        events = db.query('events', {'title': sys.argv[1]})
        info(events[0], sys.argv[2], short='-s' in sys.argv[1:])
    except:
        print('duplicates.py "title of event" key')
        sys.exit(1)

if __name__ == '__main__':
    run()
