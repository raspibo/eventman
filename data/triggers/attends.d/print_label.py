#!/usr/bin/env python
"""print_label.py - print a label with the name, the company and the person_id (in a barcode) of an attendee

Copyright 2015 Emiliano Mattioli <oloturia AT gmail.com>
               Davide Alberani <da@erlug.linux.it>
               RaspiBO <info@raspibo.org>

Licensed under the Apache License 2.0
"""

import os
import sys
import cups
import time
import tempfile
from PIL import Image, ImageFont, ImageDraw

KEEP_IMG = True
LABEL_WIDTH = 6744
LABEL_HEIGHT = 1872

FONT_TEXT = 'Ubuntu-C.ttf'
#FONT_TEXT = 'CONCIBB_.TTF'
FONT_TEXT_ENCODING = 'latin-1'
FONT_BARCODE = 'free3of9.ttf'

PRINTER_NAME = None
PRINTER_NAME = 'DYMO_LabelWriter_450'


def debug(msg):
    print '%s: %s' % (time.time(), msg)


def _get_resource(filename):
    return os.path.join(os.path.dirname(sys.argv[0]), filename)


def build_label(w, h, barcode_text, line1, line2, font_text=FONT_TEXT, font_barcode=FONT_BARCODE):
    debug('build_label start')
    barcode_text = "*" + barcode_text + "*"
    line1 = unicode(line1, 'utf-8').encode(FONT_TEXT_ENCODING, 'ignore')
    line2 = unicode(line2, 'utf-8').encode(FONT_TEXT_ENCODING, 'ignore')
    fontbar = ImageFont.truetype(_get_resource(font_barcode), 1000)
    fontname = ImageFont.truetype(_get_resource(font_text), 550)
    fontjob = ImageFont.truetype(_get_resource(font_text), 360)
    debug('build_label font done')
    image = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    wbar, hbar = draw.textsize(barcode_text, font=fontbar)
    wnorm1, hnorm1 = draw.textsize(line1, font=fontname)
    wnorm2, hnorm2 = draw.textsize(line2, font=fontjob)
    debug('build_label height calc done')
    draw.text(((w-wnorm1)/2, -670+(h-hnorm1)/2), line1, (0, 0, 0), font=fontname)
    draw.text(((w-wnorm2)/2, -220+(h-hnorm2)/2), line2, (0, 0, 0), font=fontjob)
    draw.text(((w-wbar)/2, 425+(h-hbar)/2), barcode_text, (0, 0, 0), font=fontbar)
    debug('build_label draw text done')
    if not KEEP_IMG:
        tmpfile = tempfile.NamedTemporaryFile(prefix='eventman_print_label_', suffix='.png')
    else:
        tmpfile = tempfile.mktemp(prefix='eventman_print_label_', suffix='.png')
        tmpfile = open(tmpfile, 'wb')
    image.save(tmpfile, dpi=[600, 300], format='png')
    debug('build_label end')
    return tmpfile


def print_label(label_file, name):
    debug('print_label start')
    conn = cups.Connection()
    printer = PRINTER_NAME or conn.getDefault()
    debug('print_label connection done')
    conn.printFile(printer, label_file.name, name, {})
    debug('print_label end')


def run():
    debug('run start')
    # Always consume stdin.
    sys.stdin.read()
    name = ' '.join([os.environ.get('NAME') or '', os.environ.get('SURNAME') or ''])
    company = os.environ.get('COMPANY') or ''
    # Print the decimal value SEQ as an hex of at least 6 digits.
    seq = os.environ.get('SEQ_HEX', '0')
    label_file = build_label(LABEL_WIDTH, LABEL_HEIGHT, seq, name, company)
    print_label(label_file, name)
    debug('run end')


if __name__ == '__main__':
    try:
        run()
    except Exception, e:
        sys.stderr.write('print_label.  Exception raised: %s\n' % e)

