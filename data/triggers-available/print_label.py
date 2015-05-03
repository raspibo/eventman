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
import tempfile
from PIL import Image, ImageFont, ImageDraw

KEEP_IMG = False
LABEL_WIDTH = 13488
LABEL_HEIGHT = 3744

FONT_TEXT = 'Ubuntu-C.ttf'
FONT_TEXT_ENCODING = 'latin-1'
FONT_BARCODE = 'free3of9.ttf'

PRINTER_NAME = None
PRINTER_NAME = 'DYMO_LabelWriter_450'


def _get_resource(filename):
    return os.path.join(os.path.dirname(sys.argv[0]), filename)


def build_label(w, h, barcode_text, line1, line2, font_text=FONT_TEXT, font_barcode=FONT_BARCODE):
    barcode_text = "*" + barcode_text + "*"
    line1 = unicode(line1, 'utf-8').encode(FONT_TEXT_ENCODING, 'ignore')
    line2 = unicode(line2, 'utf-8').encode(FONT_TEXT_ENCODING, 'ignore')
    fontbar = ImageFont.truetype(_get_resource(font_barcode), 2200)
    fontnorm = ImageFont.truetype(_get_resource(font_text), 780)
    image = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    wbar, hbar = draw.textsize(barcode_text, font=fontbar)
    wnorm1, hnorm1 = draw.textsize(line1, font=fontnorm)
    wnorm2, hnorm2 = draw.textsize(line2, font=fontnorm)
    draw.text(((w-wnorm1)/2, -1200+(h-hnorm1)/2), line1, (0, 0, 0), font=fontnorm)
    draw.text(((w-wnorm2)/2, -450+(h-hnorm2)/2), line2, (0, 0, 0), font=fontnorm)
    draw.text(((w-wbar)/2, 850+(h-hbar)/2), barcode_text, (0, 0, 0), font=fontbar)
    if not KEEP_IMG:
        tmpfile = tempfile.NamedTemporaryFile(prefix='eventman_print_label_', suffix='.png')
    else:
        tmpfile = tempfile.mktemp(prefix='eventman_print_label_', suffix='.png')
        tmpfile = open(tmpfile, 'wb')
    image.save(tmpfile, dpi=[600, 300], format='png')
    return tmpfile


def print_label(label_file, name):
    conn = cups.Connection()
    printer = PRINTER_NAME or conn.getDefault()
    conn.printFile(printer, label_file.name, name, {})


def run():
    # Always consume stdin.
    sys.stdin.read()
    name = ' '.join([os.environ.get('NAME') or '', os.environ.get('SURNAME') or ''])
    company = os.environ.get('COMPANY') or ''
    # Print the decimal value SEQ as an hex of at least 6 digits.
    seq = os.environ.get('SEQ_HEX', '0')
    label_file = build_label(LABEL_WIDTH, LABEL_HEIGHT, seq, name, company)
    print_label(label_file, name)


if __name__ == '__main__':
    try:
        run()
    except Exception, e:
        sys.stderr.write('print_label.  Exception raised: %s\n' % e)

