"""Operator-run signing-key rotation; no key values are printed."""

import argparse
import os
import secrets

import pymongo
from pymongo.errors import PyMongoError


def rotate_cookie_secret(settings):
    """Replace the signing key for one existing setting record."""
    records = list(settings.find({'setting': 'server_cookie_secret'}, {'_id': 1}).limit(2))
    if len(records) != 1:
        raise ValueError('Expected exactly one signing-key record')
    result = settings.update_one({'_id': records[0]['_id']},
                                 {'$set': {'cookie_secret': secrets.token_urlsafe(48)}})
    if result.matched_count != 1:
        raise ValueError('Signing-key record no longer exists')


def main():
    parser = argparse.ArgumentParser(description='Rotate the signing key; invalidates login cookies after restart.')
    parser.add_argument('--db-name', default='eventman')
    parser.add_argument('--yes', action='store_true', help='acknowledge session invalidation and required restart')
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit('Rotation requires --yes; stop EventMan and plan session invalidation first')
    try:
        with pymongo.MongoClient(os.environ.get('EVENTMAN_MONGO_URL'),
                                serverSelectionTimeoutMS=10_000) as client:
            rotate_cookie_secret(client[args.db_name]['settings'])
    except (PyMongoError, ValueError):
        raise SystemExit('Unable to rotate signing key; check database access and that exactly one key record exists') from None
    print('Signing key rotated; restart all EventMan processes. Existing login cookies will be invalid.')


if __name__ == '__main__':
    main()
