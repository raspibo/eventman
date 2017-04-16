#!/usr/bin/env python3

import sys
import monco

def info(event):
    tickets = event['tickets']
    total = 0
    attended = 0
    afternoon = 0
    for ticket in tickets:
        if ticket.get('cancelled'):
            continue
        email = ticket.get('email')
        if ticket.get('attended'):
            attended += 1
        if ticket.get('afternoon_attended'):
            afternoon += 1
        total += 1
    title = event['title']
    print('Total registered: %d' % total)
    print('Attendees: %d' % attended)
    print('Afternoon: %d' % afternoon)
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
