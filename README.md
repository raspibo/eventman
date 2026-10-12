# EventMan(ager)

Your friendly manager of attendees at an event.

EventMan(ager) will help you handle your list of attendees at an event, managing the list of tickets and marking persons as present.

Main features:
- an admin (in the future: anyone) can create and manage new events
- events can define a registration form with many custom fields
- a person can join (or leave) an event, submitting the custom forms
- no registration is required to join/leave an event
- quickly mark a registered person as an attendee
- easy way to add a new ticket, if it's already known from a previous event or if it's a completely new ticket
- set maximum number of tickets and begin/end date for sales
- can import from Eventbrite using API and CSV file; see the docs/Eventbrite\_import.md file
- RESTful interface that can be called by third-party applications
- ability to run triggers to respond to an event (e.g. when a person is marked as attending to an event)
- can run on HTTPS
- multiple workstations are kept in sync (i.e.: marking a person as an attendee is shown in every workstation currently viewing the list of tickets of an event)
- can run in Docker: see the docs/DOCKER.md file

See the *screenshots* directory for some images.


# Development

See the *docs/DEVELOPMENT.md* file for more information about how to contribute.


# Technological stack

- [Python 3](https://www.python.org/) for the backend
- Modern standards-based HTML, CSS and ES modules for the webApp (no browser-side framework or build step)
- [Tornado web](http://www.tornadoweb.org/) as web server
- [MongoDB](https://www.mongodb.org/) to store the data

The web part is included; you need Python 3.10+ and a separately running MongoDB server.
Python dependencies are declared in `requirements.txt`, with separate requirement files for optional features. See [dependency and distribution details](docs/DEPENDENCIES.md).


# Install and run

## Docker

For first-time setup, configure the initial admin password file as described in
[the Docker instructions](docs/DOCKER.md#initial-admin-password). Existing
databases with an admin need no bootstrap password. Then run:

    docker compose up --build


## Old-fashioned installation

Be sure to have a running MongoDB server locally. Install into a virtual environment:

    git clone https://github.com/raspibo/eventman
    cd eventman
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -r requirements.txt
    ./eventman_server.py --debug --admin_password_file=/absolute/private/admin-password

Before first startup, create that UTF-8 file outside the checkout with your chosen
password on one line and permissions 0600. The server account must be able to
read it. A final newline is allowed; spaces in the password are preserved.
Once the admin exists, the file option can be removed.

Optional features can be installed in the same environment:

    python -m pip install -r requirements-eventbrite.txt # Eventbrite API imports
    python -m pip install -r requirements-scanner.txt    # serial QR/barcode reader
    python -m pip install -r requirements-printing.txt   # label printing

Label printing also needs system CUPS headers to build pycups, a configured printer,
and externally installed fonts. See [the printing setup](docs/DEPENDENCIES.md#label-printing).

Open browser and navigate to: http://localhost:5242/

If you store SSL key and certificate in the *ssl* directory (default names: eventman\_key.pem and eventman\_cert.pem), HTTPS will be used: https://localhost:5242/


# Basic workflow

So, you've just installed it and you have the server running.  Let's create an event:
- login with the **admin** user using the password supplied at first startup
- click "Add an event"
- edit basic information about the event and save it
- a default registration form is provided, with the following fields (all are optional):
  - Name
  - Surname
  - Email
  - Job title
  - Company
- if you want to customize it, go to the second panel ("Registration form") and edit it:
  - first, define how many rows the form will have
  - then define how many columns will be in each rows
  - now edit every form field
  - give a name to the form (not really meaningful) and save it

Now persons can start joining your event:
- click on "Join this event" in the list of events
- compile the form and submit it
- the user will have to keep the provided link, if they want to edit their information later
- from this link, a person can also mark a ticket as "cancelled" (not counted in the list of tickets), or they can enable it again
- if the person was a registered user, it's possible to see the list of own tickets in the personal page

As an administrator, you can now go to the list of tickets of the event:
- from there, once the event has started, you can mark persons as attendees
- it's also possible to quickly add a new ticket or delete an existing one (the ticket is effectively deleted, it's not the same as the cancelled action)


## Notes on some special features

Some notes about the event registration form:
- field names are important (case is not considered). You can use whatever you want, but "name", "surname" and "email" are internally used to show the tickets list, so please add at least one of them

About the "Group ID" of events and "Unregistered persons" list:
- "Group ID" is a random non-guessable identifier associated to an event. You can use whatever you want; if left empty, it will be autogenerated. It's not the same as the Event ID (the \_id key in the db): the Group ID is supposed to be secret
- if two or more events share the same Group ID, persons that are registered in others events and are not present in the list of tickets you're looking for are added to the list of "Unregistered persons" to quickly add them. For example: if you are managing the third edition of a series of events, you can set the same Group ID to every event, and then you can quickly add a person that was present at a previous edition
- in the "Unregistered persons" list there will also be deleted tickets (beware that they are transitory: if the page is refreshed, they'll be gone for good); to match tickets between the list of tickets and "Unregistered persons" list, the email field is used, if present


# Authentication

Authentication is required by default. Unregistered and unprivileged users can see and join events, but are unable to edit or handle them. Administrator users can create and edit events; more information about how permissions are handled can be found in the *docs/DEVELOPMENT.md* file. Use `--authentication=false` only for a deliberately public deployment.

On first startup, supply the **admin** password using `--admin_password_file`
(recommended) or the existing `--admin_password` option. Both options can also
be set in a Tornado configuration file. Passwords are never printed to logs.
Startup fails before creating the admin if neither supplies a password, if both
are supplied, or if the password file is unreadable, empty, or contains multiple
lines. Keep secret files outside the checkout with owner-only access; passwords
passed directly on the command line may be visible in shell history and process
listings. Existing admins are not changed, and their startup ignores bootstrap
inputs. Legacy SHA-512 password hashes are no longer accepted for login; affected
accounts require an operator-managed reset to PBKDF2-SHA256. See
[password retirement and recovery](tools/README.md#password-retirement-and-recovery)
for read-only inventory and reset commands, including recovery for an admin.

Users can register, but are not forced to do so: tickets can also be issued to unregistered persons. However, if you register, you'll be able to access the list of all of your tickets (otherwise, you have to save the tickets' link, if you want to edit them later).

# Web interface

The current interface is a responsive, dependency-free ES module application. It uses native browser controls, keyboard-accessible navigation, `fetch`, WebSockets and the server's XSRF protection. The first-party legacy AngularJS source remains as historical reference; its third-party libraries have been removed from the source tree and are available in Git history. The Docker image includes only the active frontend.

Existing event registration schemas are rendered for attendees. The legacy visual schema editor has been retired; create or update schemas through the API until a replacement editor is introduced.

# Tools

In the 'tools' directory there are some useful tools, to handle check-in and extract data.


# Other projects

Needs something simpler, that just allows you to register attendees at an event?  Try [ibt2](https://github.com/raspibo/ibt2)


# License and copyright

Copyright 2015-2026 Davide Alberani <da@mimante.net>, RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
