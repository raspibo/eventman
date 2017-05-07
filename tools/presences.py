#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import operator
import itertools
import monco

EVENTS = ('HackInBo 2015', 'HackInBo 2015 Winter', 'HackInBo 2016', 'HackInBo 2016 Winter', 'HackInBo 2017')
NEXT_EVENT = '' # leave it empty if we've not yet added the tickets for the next event

all_tickets = {}

db = monco.Monco(dbName='eventman')

class Info(object):
    def __init__(self, registered=0, attended=0):
        self.registered = registered
        self.attended = attended

    def __lt__(self, other):
        return self.registered < other.registered or self.attended < other.attended

    def __str__(self):
        return '%d of %d' % (self.registered, self.attended)

    def __eq__(self, other):
        return self.registered == other.registered and self.attended == other.attended

    def __hash__(self):
        return hash((self.registered, self.attended))

event_data = {}

for event_name in EVENTS:
    event = db.query('events', {'title': event_name})[0]
    event_tickets = event['tickets']
    uniq = set()
    new_in_this = 0
    event_data[event_name] = {'registered': 0, 'attended': 0, 'new_in_this': 0}
    for ticket in event_tickets:
        if ticket.get('cancelled'):
            continue
        event_data[event_name]['registered'] += 1
        unique_name = '%s %s' % (ticket.get('name', '').lower(), ticket.get('surname', '').lower())
        if unique_name in uniq:
            continue
        uniq.add(unique_name)
        attended = ticket.get('attended')
        if unique_name not in all_tickets:
            all_tickets[unique_name] = {'registered': 0, 'attended': 0}
            all_tickets[unique_name] = Info()
            if attended:
                event_data[event_name]['new_in_this'] += 1
                new_in_this += 1
        all_tickets[unique_name].registered += 1
        if attended:
            event_data[event_name]['attended'] += 1
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

print('New persons at each event:')
for event_name in EVENTS:
    new_in_this = event_data[event_name]['new_in_this']
    attended = event_data[event_name]['attended']
    percent = 0
    if attended:
        percent = new_in_this / attended * 100
    print('%s: %d persons never seen before (%d total attended, %d%%)' % (event_name, new_in_this,
                                                                    attended, percent))

print('')
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

all_morons = {}
grouped_morons = itertools.groupby(sorted(morons_combinations, key=operator.itemgetter(0), reverse=True),
                                   operator.itemgetter(0))

for i in (item for sublist in grouped_morons for item in sublist[1]):
    morons = Info(*i)
    print('')
    print('Morons (registered at %d events, attended %d):' % (i[0], i[1]))
    for p, info in sorted(all_tickets.items()):
        if info == morons:
            all_morons[p] = info
            print(p)

if next_event_names:
    print('')
    morons_to_next_event = set()
    for name in sorted(next_event_names):
        if name in all_morons:
            morons_to_next_event.add((name, all_morons[name]))
    print('Morons registered at the next event (%d morons):' % len(morons_to_next_event))
    for m, info in sorted(morons_to_next_event):
        print('%s (%s)' % (m, info))
