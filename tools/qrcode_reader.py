#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qrcode_reader

Scan the output of a serial QR Code reader.

Copyright 2017 Davide Alberani <da@erlug.linux.it>
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

import os
import io
import sys
import time
import serial
import urllib
import requests
import configparser


class Connector():
    def __init__(self, cfg):
        self.cfg = cfg
        self.session = None
        self.url = cfg['eventman']['url']
        self.login_url = urllib.parse.urljoin(self.url, '/v1.0/login')
        self.checkin_url = urllib.parse.urljoin(self.url, os.path.join('/v1.0/events/',
                                                cfg['event']['id'], 'tickets/'))
        self.login()

    def login(self):
        try:
            self.session = requests.Session()
            self.session.verify = False
            ca = cfg['eventman'].get('ca')
            if ca and os.path.isfile(ca):
                self.session.verify = ca
            username = cfg['eventman'].get('username')
            password = cfg['eventman'].get('password')
            params = {}
            if username:
                params['username'] = username
            if password:
                params['password'] = password
            req = self.session.post(self.login_url, json=params)
            req.raise_for_status()
            req.connection.close()
        except requests.exceptions.ConnectionError as ex:
            print('unable to connect to %s: %s' % (self.login_url, ex))
            sys.exit(1)

    def checkin(self, code):
        limit_field = self.cfg['event'].getint('limit_field')
        if limit_field:
            code = code[:limit_field]
        checkin_url = self.checkin_url + '?' + urllib.parse.urlencode({cfg['event']['field']: code})
        params = dict(self.cfg['actions'])
        req = self.session.put(checkin_url, json=params)
        try:
            req.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            print('error: %s' % req.json().get('message'))
        req.connection.close()


def scan(port):
    retry = 1
    while True:
        print('waiting for connection on port %s...' % port)
        try:
            ser = serial.Serial(port=port, timeout=1)
            break
        except serial.serialutil.SerialException as ex:
            if retry >= 10:
                print('unable to connect: %s' % ex)
                sys.exit(2)
        time.sleep(1)
        retry += 1
    print('connected to %s' % port)
    ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1), newline='\r', line_buffering=True)
    while True:
        line = ser_io.readline().strip()
        if not line:
            continue
        yield line


if __name__ == '__main__':
    cfg = configparser.ConfigParser()
    cfg.read('qrcode_reader.ini')
    connector = Connector(cfg)
    try:
        for code in scan(port=cfg['connection']['port']):
            print('received code %s' % code)
            connector.checkin(code)
    except KeyboardInterrupt:
        print('exiting...')
