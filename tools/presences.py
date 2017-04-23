#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import operator
import itertools
import monco

EVENTS = ('HackInBo 2015', 'HackInBo 2015 Winter', 'HackInBo 2016', 'HackInBo 2016 Winter')
NEXT_EVENT = 'HackInBo 2017' # leave it empty if we've not yet added the tickets for the next event

all_tickets = {}

db = monco.Monco(dbName='eventman')

class Info(object):
    def __init__(self, registered=0, attended=0):
        self.registered = registered
        self.attended = attended

    def __lt__(self, other):
        return self.registered < other.registered or self.attended < other.attended

    def __str__(self):
        return 'registered at %d events and attended at %d' % (self.registered, self.attended)

    def __eq__(self, other):
        return self.registered == other.registered and self.attended == other.attended

    def __hash__(self):
        return hash((self.registered, self.attended))

for event_name in EVENTS:
    event = db.query('events', {'title': event_name})[0]
    event_tickets = event['tickets']
    uniq = set()
    for ticket in event_tickets:
        if ticket.get('cancelled'):
            continue
        unique_name = '%s %s' % (ticket.get('name', '').lower(), ticket.get('surname', '').lower())
        if unique_name in uniq:
            continue
        uniq.add(unique_name)
        if unique_name not in all_tickets:
            all_tickets[unique_name] = {'registered': 0, 'attended': 0}
            all_tickets[unique_name] = Info()
        all_tickets[unique_name].registered += 1
        if ticket.get('attended'):
            all_tickets[unique_name].attended += 1

values = list(all_tickets.values())
unique = set(values)

next_event_names = set()
if NEXT_EVENT:
    event = db.query('events', {'title': NEXT_EVENT})[0]
    event_tickets = event['tickets']
    for ticket in event_tickets:
        if ticket.get('cancelled'):
            continue
        unique_name = '%s %s' % (ticket.get('name', '').lower(), ticket.get('surname', '').lower())
        next_event_names.add(unique_name)

print('Total persons:', len(values))
print('')
res = []
for comb in unique:
    items = values.count(comb)
    res.append((items, '%04s persons %s' % (items, comb)))
for items, s in sorted(res, reverse=True):
    print(s)

combinations = itertools.combinations(range(len(EVENTS) + 1), 2)
morons_combinations = []
for presences, registrations in combinations:
    if registrations < 3:
        continue
    if registrations - presences <= 1:
        continue
    morons_combinations.append((registrations, presences))

all_morons = set()
grouped_morons = itertools.groupby(sorted(morons_combinations, key=operator.itemgetter(0), reverse=True),
                                   operator.itemgetter(0))

for i in (item for sublist in grouped_morons for item in sublist[1]):
    morons = Info(*i)
    print('')
    print('Morons (registered at %d events, attended %d):' % (i[0], i[1]))
    for p, info in all_tickets.items():
        if info == morons:
            all_morons.add(p)
            print(p)

if next_event_names:
    print('')
    morons_to_next_event = set()
    for name in sorted(next_event_names):
        if name in all_morons:
            morons_to_next_event.add(name)
    print('Morons registered at the next event (%d morons):' % len(morons_to_next_event))
    for m in morons_to_next_event:
        print(m)
