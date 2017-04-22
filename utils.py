# -*- coding: utf-8 -*-
"""EventMan(ager) utils

Miscellaneous utilities.

Copyright 2015-2016 Davide Alberani <da@erlug.linux.it>
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
            headers[idx] = header.lower().replace(' ', '_')
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

