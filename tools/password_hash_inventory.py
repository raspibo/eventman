"""Read-only password-format counts. Run with python3 -m tools.password_hash_inventory."""

import argparse
import json
import os

import pymongo
from pymongo.errors import PyMongoError

from utils import password_hash_kind


def inventory(users):
    """Count stored password formats without returning users or hashes.

    :param users: MongoDB users collection
    :returns: counts by password format and total users
    """
    counts = dict(pbkdf2_sha256=0, legacy_sha512=0, missing=0, unrecognized=0)
    for user in users.find({}, {'_id': 0, 'password': 1}):
        counts[password_hash_kind(user.get('password'))] += 1
    return dict(total=sum(counts.values()), **counts)


def main():
    parser = argparse.ArgumentParser(description='Report password-format counts without user or hash values.')
    parser.add_argument('--db-name', default='eventman', help='MongoDB database name')
    args = parser.parse_args()
    try:
        with pymongo.MongoClient(os.environ.get('EVENTMAN_MONGO_URL'),
                                serverSelectionTimeoutMS=10_000) as client:
            counts = inventory(client[args.db_name]['users'])
    except (PyMongoError, ValueError):
        # Driver errors can include credentials from the connection URI.
        raise SystemExit('Unable to inventory password formats; check MongoDB access and configuration') from None
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
