"""Operator-managed password reset. Run with python3 -m tools.reset_user_password."""

import argparse
import getpass
import os
import sys
import warnings

import pymongo
from pymongo.errors import PyMongoError

from utils import hash_password


def reset_password(users, username, password):
    """Replace one account's password, preserving its identity and permissions.

    :param users: MongoDB users collection
    :param username: exact account username
    :param password: new cleartext password
    """
    if not password:
        raise ValueError('The new password must not be empty')
    matches = list(users.find({'username': username}, {'_id': 1}).limit(2))
    if len(matches) != 1:
        raise ValueError('Expected exactly one matching account; no password was changed')
    result = users.update_one({'_id': matches[0]['_id']},
                              {'$set': {'password': hash_password(password)}})
    if result.matched_count != 1:
        raise ValueError('Account no longer exists; no password was changed')


def main():
    parser = argparse.ArgumentParser(description='Reset one account password using a hidden terminal prompt.')
    parser.add_argument('--username', required=True, help='exact username to reset')
    parser.add_argument('--db-name', default='eventman', help='MongoDB database name')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        raise SystemExit('Use an interactive terminal for the hidden password prompts')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            password = getpass.getpass('New password: ')
            confirmation = getpass.getpass('Confirm new password: ')
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        raise SystemExit('Unable to read a password securely; no password was changed') from None
    if not password:
        raise SystemExit('The new password must not be empty')
    if password != confirmation:
        raise SystemExit('Passwords do not match; no password was changed')
    try:
        with pymongo.MongoClient(os.environ.get('EVENTMAN_MONGO_URL'),
                                serverSelectionTimeoutMS=10_000) as client:
            reset_password(client[args.db_name]['users'], args.username, password)
    except PyMongoError:
        raise SystemExit('Unable to reset password; check MongoDB access and configuration') from None
    except ValueError:
        # Avoid exposing driver configuration errors, which may contain URI secrets.
        raise SystemExit('Unable to reset password; check configuration and that exactly one account matches') from None
    print('Password reset complete')


if __name__ == '__main__':
    main()
