# -*- coding: utf-8 -*-
"""EventMan(ager) utils

Miscellaneous utilities.

Copyright 2015-2017 Davide Alberani <da@erlug.linux.it>
                    RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import csv
import copy
import json
import string
import random
import hashlib
import datetime
import io
from bson.objectid import ObjectId


def csvParse(csvStr, remap=None, merge=None):
    """Parse a CSV file, optionally renaming the columns and merging other information.

    :param csvStr: the CSV to parse, as a string
    :type csvStr: str
    :param remap: a dictionary used to rename the columns
    :type remap: dict
    :param merge: merge these information into each line
    :type merge: dict

    :returns: tuple with a dict of total and valid lines and the data
    :rtype: tuple
    """
    if isinstance(csvStr, bytes):
        csvStr = csvStr.decode('utf-8')
    fd = io.StringIO(csvStr)
    reader = csv.reader(fd)
    remap = remap or {}
    merge = merge or {}
    fields = 0
    reply = dict(total=0, valid=0)
    results = []
    try:
        headers = next(reader)
        fields = len(headers)
    except (StopIteration, csv.Error):
        return reply, {}

    for idx, header in enumerate(headers):
        if header in remap:
            headers[idx] = remap[header]
        else:
            headers[idx] = header.lower().replace(' ', '_').replace('.', '_')
    try:
        for row in reader:
            try:
                reply['total'] += 1
                if len(row) != fields:
                    continue
                values = dict(zip(headers, row))
                values.update(merge)
                results.append(values)
                reply['valid'] += 1
            except csv.Error:
                continue
    except csv.Error:
        pass
    fd.close()
    return reply, results


def hash_password(password, salt=None):
    """Hash a password.

    :param password: the cleartext password
    :type password: str
    :param salt: the optional salt (randomly generated, if None)
    :type salt: str

    :returns: the hashed password
    :rtype: str"""
    if salt is None:
        salt_pool = string.ascii_letters + string.digits
        salt = ''.join(random.choice(salt_pool) for x in range(32))
    pwd = '%s%s' % (salt, password)
    hash_ = hashlib.sha512(pwd.encode('utf-8'))
    return '$%s$%s' % (salt, hash_.hexdigest())


has_eventbrite_sdk = False
try:
    from eventbrite import Eventbrite
    has_eventbrite_sdk = True
except ImportError:
    Eventbrite = object


class CustomEventbrite(Eventbrite):
    """Custom methods to override official SDK limitations; code take from Yuval Hager; see:
        https://github.com/eventbrite/eventbrite-sdk-python/issues/18

    This class should be removed onces the official SDK supports pagination.
    """
    def custom_get_event_attendees(self, event_id, status=None, changed_since=None, page=1):
        data = {}
        if status:
            data['status'] = status
        if changed_since:
            data['changed_since'] = changed_since
        data['page'] = page
        return self.get("/events/{0}/attendees/".format(event_id), data=data)

    def get_all_event_attendees(self, event_id, status=None, changed_since=None):
        page = 1
        attendees = []
        while True:
            r = self.custom_get_event_attendees(event_id, status, changed_since, page=page)
            attendees.extend(r['attendees'])
            if r['pagination']['page_count'] <= page:
                break
            page += 1
        return attendees


KEYS_REMAP = {
    ('capacity', 'number_of_tickets'),
    ('changed', 'updated_at', lambda x: x.replace('T', ' ').replace('Z', '')),
    ('created', 'created_at', lambda x: x.replace('T', ' ').replace('Z', '')),
    ('description', 'description', lambda x: x.get('text', ''))
}

def reworkObj(obj, kind='event'):
    """Rename and fix some key in the data from the Eventbrite API."""
    for remap in KEYS_REMAP:
        transf = lambda x: x
        if len(remap) == 2:
            old, new = remap
        else:
            old, new, transf = remap
        if old in obj:
            obj[new] = transf(obj[old])
            if old != new:
                del obj[old]
    if kind == 'event':
        if 'name' in obj:
            obj['title'] = obj.get('name', {}).get('text') or ''
            del obj['name']
        if 'start' in obj:
            t = obj['start'].get('utc') or ''
            obj['begin_date'] = obj['begin_time'] = t.replace('T', ' ').replace('Z', '')
        if 'end' in obj:
            t = obj['end'].get('utc') or ''
            obj['end_date'] = obj['end_time'] = t.replace('T', ' ').replace('Z', '')
    else:
        profile = obj.get('profile') or {}
        complete_name = profile['name']
        obj['surname'] = profile.get('last_name') or ''
        obj['name'] = profile.get('first_name') or ''
        if not (obj['surname'] and obj['name']):
            obj['surname'] = complete_name
        obj['email'] = profile.get('email') or ''
    return obj


def expandBarcodes(attendees):
    """Generate an attendee for each barcode in the Eventbrite API data."""
    for attendee in attendees:
        barcodes = attendee.get('barcodes') or []
        if not barcodes:
            yield attendee
        barcodes = [b.get('barcode') for b in barcodes if b.get('barcode')]
        for code in barcodes:
            att_copy = copy.deepcopy(attendee)
            att_copy['order_nr'] = code
            yield att_copy


def ebAPIFetch(oauthToken, eventID):
    """Fetch an event, complete with all attendees using Eventbrite API.

    :param oauthToken: Eventbrite API key
    :type oauthToken: str
    :param eventID: Eventbrite ID of the even to be fetched
    :type eventID: str

    :returns: information about the event and all its attendees
    :rtype: dict
    """
    if not has_eventbrite_sdk:
        raise Exception('unable to import eventbrite module')
    eb = CustomEventbrite(oauthToken)
    event = eb.get_event(eventID)
    eb_attendees = eb.get_all_event_attendees(eventID)
    event = reworkObj(event, kind='event')
    attendees = []
    for eb_attendee in eb_attendees:
        reworkObj(eb_attendee, kind='attendee')
        attendees.append(eb_attendee)
    event['eb_event_id'] = eventID
    attendees = list(expandBarcodes(attendees))
    info = {'event': event, 'attendees': attendees}
    return info


class ImprovedEncoder(json.JSONEncoder):
    """Enhance the default JSON encoder to serialize datetime and ObjectId instances."""
    def default(self, o):
        if isinstance(o, bytes):
            try:
                return o.decode('utf-8')
            except:
                pass
        elif isinstance(o, (datetime.datetime, datetime.date,
                datetime.time, datetime.timedelta, ObjectId)):
            try:
                return str(o)
            except Exception:
                pass
        elif isinstance(o, set):
            return list(o)
        return json.JSONEncoder.default(self, o)


# Inject our class as the default encoder.
json._default_encoder = ImprovedEncoder()

