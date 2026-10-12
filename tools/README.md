EventMan(ager) tools
====================

qrcode_reader
=============

With this tool, you can use a serial QR Code or barcode scanner to automarically check-in attendees.

From the repository root, in the activated virtual environment, install the scanner dependencies (`pyserial` provides `serial`):

    python -m pip install -r requirements-scanner.txt

count
=====

Just print some stats about an event.

## Password retirement and recovery

Legacy SHA-512 login support has been removed. Affected accounts keep their
identity, registrations, and permissions, but cannot log in until an operator
resets their password. This includes a legacy-only admin: `--admin_password_file`
only creates an absent admin and does not reset an existing one.

Run these commands from the repository root with core requirements installed.
Both tools use `EVENTMAN_MONGO_URL` if set, otherwise local MongoDB, and accept
`--db-name` (default `eventman`). Supply connection credentials through your
protected environment configuration; do not place them in command arguments or
commit them to the repository.

The default Compose setup does not expose MongoDB's port on the host. A local
Python command using its default `localhost:27017` cannot reach that database;
use the Docker commands below instead. `mongodb://mongo` resolves on the Compose
network, not from the host. A connection timeout now reports `Cannot reach
MongoDB`; this is distinct from an unmatched account or an incorrect password.

Before deploying the login change, inventory the intended database:

```sh
python3 -m tools.password_hash_inventory --db-name eventman
```

This command is read-only and prints JSON counts: `total`, `pbkdf2_sha256`,
`legacy_sha512`, `missing`, and `unrecognized`. It reads a password-only projection
to recognize formats and never prints usernames, IDs, or hashes. Format counts
are not a password-strength audit. Investigate missing/unrecognized values with
operator-controlled database access without exporting credentials or hashes.

Preserve a protected database backup before an approved reset. Reset one exact
account from an interactive terminal:

```sh
python3 -m tools.reset_user_password --username admin --db-name eventman
```

The tool prompts twice without echoing the new password, rejects empty or
mismatched input, and refuses insecure prompt fallback. It requires exactly one
matching account and updates only its password by ID, using a new random salt
and PBKDF2. It does not create an account or change permissions. Use the same
command with each affected account's username and arrange private delivery of
its new password. An error or zero matching account is not a successful reset;
verify login after each reset and rerun the inventory when finished.

For Docker, build the reviewed image first. The image does not contain `tools/`,
so mount the checkout's tools read-only and override the entrypoint to run these
operator commands, without starting the application or invoking triggers:

```sh
docker compose build eventman
docker compose run --rm --entrypoint python -e EVENTMAN_MONGO_URL=mongodb://mongo -v "$PWD/tools:/eventman/tools:ro" eventman -m tools.password_hash_inventory
docker compose run --rm --entrypoint python -e EVENTMAN_MONGO_URL=mongodb://mongo -v "$PWD/tools:/eventman/tools:ro" eventman -m tools.reset_user_password --username admin
```

The reset command needs an interactive terminal. The examples use the default
Compose MongoDB service/database; adapt the protected environment and database
name to the actual deployment. Building the image does not restart the running
application. Use inventory/reset before restarting it with the login change.

New hash creation accepts only `hash_password(password)`; the old explicit-salt
SHA-512 creation API is removed. External helper scripts using `salt=` must be
updated. Do not hash an old digest as if it were the user's password. If rollback
is needed, use a revision supporting PBKDF2, and do not restore weaker hashes
over successfully reset accounts. No real account reset is part of repository
validation; deployment inventory/reset and login checks are owner-operated.
