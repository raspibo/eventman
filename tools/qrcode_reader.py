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
import logging
import argparse
import requests
import configparser
from requests.packages.urllib3.exceptions import InsecureRequestWarning


logger = logging.getLogger('qrcode_reader')
logging.basicConfig(level=logging.INFO)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def convert_obj(obj):
    try:
        return int(obj)
    except:
        pass
    if isinstance(obj, str):
        obj_l = obj.lower()
        if obj_l in ['true', 'on', 'yes']:
            return True
        elif obj_l in ['false', 'off', 'no']:
            return False
    return obj


def convert(seq):
    if isinstance(seq, dict):
        d = {}
        for key, item in seq.items():
            d[key] = convert(item)
        return d
    if isinstance(seq, (list, tuple)):
        return [convert(x) for x in seq]
    return convert_obj(seq)


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
            logger.error('unable to connect to %s: %s' % (self.login_url, ex))
            sys.exit(1)

    def checkin(self, code):
        msg = 'scanning code %s: ' % code
        limit_field = self.cfg['event'].getint('limit_field')
        if limit_field:
            code = code[:limit_field]
        params = {cfg['event']['field']: code, '_errorMessage': 'code: %s' % code}
        checkin_url = self.checkin_url + '?' + urllib.parse.urlencode(params)
        json = convert(dict(self.cfg['actions']))
        req = self.session.put(checkin_url, json=json)
        error = False
        try:
            req.raise_for_status()
            msg += 'ok'
        except requests.exceptions.HTTPError as ex:
            error = True
            msg += 'error: %s' % req.json().get('message')
        if not error:
            logger.info(msg)
        else:
            logger.warning(msg)
        req.connection.close()


def scan(port):
    retry = 1
    logger.info('trying to connect to %s, please wait...' % port)
    while True:
        logger.debug('waiting for connection on port %s...' % port)
        try:
            ser = serial.Serial(port=port, timeout=1)
            break
        except serial.serialutil.SerialException as ex:
            if retry >= 20:
                logger.error('unable to connect: %s' % ex)
                sys.exit(2)
        time.sleep(1)
        retry += 1
    logger.info('connected to %s' % port)
    ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1), newline='\r', line_buffering=True)
    while True:
        try:
            line = ser_io.readline().strip()
        except serial.serialutil.SerialException as ex:
            logger.error('disconnected: %s' % ex)
            sys.exit(3)
        if not line:
            continue
        yield line


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--code', help='specify a single code', action='store')
    parser.add_argument('--config', help='user a different configuration file (default: qrcode_reader.ini)',
                        action='store', default='qrcode_reader.ini')
    args = parser.parse_args()

    cfg = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    cfg.read(args.config)
    if cfg['qrcode_reader'].getboolean('debug'):
        logging.basicConfig(level=logging.DEBUG)
    connector = Connector(cfg)
    if args.code:
        connector.checkin(args.code)
    else:
        try:
            for code in scan(port=cfg['connection']['port']):
                connector.checkin(code)
        except KeyboardInterrupt:
            logger.info('exiting...')
