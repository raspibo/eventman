#!/usr/bin/env python3
"""print_label.py - print a label with the name, the company and SEQ_HEX (in a barcode) of an attendee

Copyright 2015-2013 Emiliano Mattioli <oloturia AT gmail.com>
                    Davide Alberani <da@mimante.net>
                    RaspiBO <info@raspibo.org>

Licensed under the Apache License 2.0
"""

import os
import sys
import cups
import tempfile
from PIL import Image, ImageFont, ImageDraw

KEEP_IMG = True
LABEL_WIDTH = 13488
LABEL_HEIGHT = 3744

# Fonts belong to the host, not the EventMan source distribution.
FONT_TEXT = os.environ.get('EVENTMAN_LABEL_TEXT_FONT')
FONT_BARCODE = os.environ.get('EVENTMAN_LABEL_BARCODE_FONT')

PRINTER_NAME = None
#PRINTER_NAME = 'DYMO_LabelWriter_450'


def _get_resource(filename):
    if not filename or not os.path.isabs(filename) or not os.path.isfile(filename):
        raise ValueError('Set EVENTMAN_LABEL_TEXT_FONT and EVENTMAN_LABEL_BARCODE_FONT '
                         'to absolute paths of externally installed fonts '
                         '(the barcode font must encode Code 39).')
    return filename


def build_label(w, h, barcode_text, line1, line2, font_text=FONT_TEXT, font_barcode=FONT_BARCODE):
    barcode_text = "*" + barcode_text + "*"
    if isinstance(line1, bytes):
        line1 = line1.decode('utf-8')
    if isinstance(line2, bytes):
        line2 = line2.decode('utf-8')
    fontbar = ImageFont.truetype(_get_resource(font_barcode), 2000)
    fontname = ImageFont.truetype(_get_resource(font_text), 1100)
    fontjob = ImageFont.truetype(_get_resource(font_text), 780)
    image = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    def text_size(text, font):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top
    wbar, hbar = text_size(barcode_text, fontbar)
    wnorm1, hnorm1 = text_size(line1, fontname)
    wnorm2, hnorm2 = text_size(line2, fontjob)
    draw.text(((w-wnorm1)/2, -1300+(h-hnorm1)/2), line1, (0, 0, 0), font=fontname)
    draw.text(((w-wnorm2)/2, -480+(h-hnorm2)/2), line2, (0, 0, 0), font=fontjob)
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
    except Exception as e:
        sys.stderr.write('print_label.  Exception raised: %s\n' % e)

