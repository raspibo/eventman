#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
import serial
import requests


class Connector():
    def __init__(self, login_url, checkin_url, username=None, password=None):
        self.login_url = login_url
        self.checkin_url = checkin_url
        self.session = requests.Session()
        json = {}
        if username:
            json['username'] = username
        if password:
            json['password'] = password
        req = self.session.post(login_url, json=json, verify=False)
        req.raise_for_status()
        req.connection.close()

    def checkin(self, code):
        req = self.session.put(self.checkin_url + '?order_nr=' + code[:9], json={'attended': True}, verify=False)
        req.raise_for_status()
        req.connection.close()



def scan():
    ser = serial.Serial(port='/dev/ttyACM0', timeout=1)
    ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1), newline='\r', line_buffering=True)
    while True:
        line = ser_io.readline().strip()
        if not line:
            continue
        yield line


if __name__ == '__main__':
    connector = Connector(login_url='https://localhost:5242/v1.0/login',
                          checkin_url='https://localhost:5242/v1.0/events/1490640884_8820477-7-7gvft6nlrs2o73fza54a6yeywiowmj8v/tickets/',
                          username='admin',
                          password='eventman')
    try:
        for code in scan():
            print(code)
            connector.checkin(code)
    except KeyboardInterrupt:
        print('exiting...')
