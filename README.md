EventMan(ager)
===============

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
- can import Eventbrite CSV export files
- RESTful interface that can be called by third-party applications (see the https://github.com/raspibo/event_man/ repository for a simple script that checks people in using a barcode/QR-code reader)
- ability to run triggers to respond to an event (e.g. when a person is marked as attending to an event)
- can run on HTTPS
- multiple workstations are kept in sync (i.e.: marking a person as an attendee is shown in every workstation currently viewing the list of tickets of an event)

See the *screenshots* directory for some images.

Demo
====

Whenever the gods of cloud-at-cost love us - very seldom, indeed - a demo system can be found at http://amy.ismito.it:5242/ (username: admin, password: eventman).


Development
===========

See the *docs/DEVELOPMENT.md* file for more information about how to contribute.


Technological stack
===================

- [Python 3](https://www.python.org/) for the backend
- [AngularJS](https://angularjs.org/) (plus some third-party modules) for the webApp
- [Angular Easy form Generator](https://mackentoch.github.io/easyFormGenerator/) for the custom forms
- [Bootstrap](http://getbootstrap.com/) (plus [Angular UI](https://angular-ui.github.io/bootstrap/)) for the eye-candy
- [Font Awesome](https://fortawesome.github.io/Font-Awesome/) for even more cuteness
- [Tornado web](http://www.tornadoweb.org/) as web server
- [MongoDB](https://www.mongodb.org/) to store the data

The web part is incuded; you need to install Tornado, MongoDB and the pymongo module on your system (no configuration needed).
If you want to print labels using the _print\_label_ trigger, you may also need the pycups module.


Install and run
===============

Be sure to have a running MongoDB server, locally. If you want to install the dependencies only locally to the current user, you can append the *--user* argument to the *pip* calls. Please also install the *python3-dev* package, before running the following commands.

    wget https://bootstrap.pypa.io/get-pip.py
    sudo python3 get-pip.py
    sudo pip3 install tornado # version 4.2 or later
    sudo pip3 install pymongo # version 3.2.2 or later
    sudo pip3 install python-dateutil
    sudo pip3 install pycups # only needed if you want to print labels
    sudo pip3 install serial # only for the qrcode_reader script
    sudo pip3 install requests # only for the qrcode_reader script
    git clone https://github.com/raspibo/eventman
    cd eventman
    ./eventman_server.py --debug


Open browser and navigate to: http://localhost:5242/

If you store SSL key and certificate in the *ssl* directory (default names: eventman\_key.pem and eventman\_cert.pem), HTTPS will be used: https://localhost:5242/


Basic workflow
==============

So, you've just installed it and you have the server running.  Let's create an event:
- login with the **admin** user (default password: **eventman**)
- click "Add an event"
- edit basic information about the event and save it
- in the second panel ("Registration form"), edit the form that will be presented to the persons that want to join your event:
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


Notes on some special features
------------------------------

Some notes about the event registration form:
- field names are important (case is not considered). You can use whatever you want, but "name", "surname" and "email" are internally used to show the tickets list, so please add at least one of them

About the "Group ID" of events and "Unregistered persons" list:
- "Group ID" is a random non-guessable identifier associated to an event. You can use whatever you want; if left empty, it will be autogenerated. It's not the same as the Event ID (the \_id key in the db): the Group ID is supposed to be secret
- if two or more events share the same Group ID, persons that are registered in others events and are not present in the list of tickets you're looking for are added to the list of "Unregistered persons" to quickly add them. For example: if you are managing the third edition of a series of events, you can set the same Group ID to every event, and then you can quickly add a person that was present at a previous edition
- in the "Unregistered persons" list there will also be deleted tickets (beware that they are transitory: if the page is refreshed, they'll be gone for good); to match tickets between the list of tickets and "Unregistered persons" list, the email field is used, if present


Authentication
==============

By default, authentication is not required; unregistered and unprivileged users can see and join events, but are unable to edit or handle them. Administrator users can create ed edit events; more information about how permissions are handled can be found in the *docs/DEVELOPMENT.md* file.

The default administrator username and password are **admin** and **eventman**. If you want to force authentication (you usually don't), run the daemon with --authentication=on

Users can register, but are not forced to do so: tickets can also be issued to unregistered persons. However, if you register, you'll be able to access the list of all of your tickets (otherwise, you have to save the tickets' link, if you want to edit them later).

Tools
=====

In the 'tools' directory there are some useful tools, to handle check-in and extract data.


License and copyright
=====================

Copyright 2015-2017 Davide Alberani <da@erlug.linux.it>, RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

