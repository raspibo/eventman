Event Man(ager)
===============

Your friendly manager of attendees at an event.

EventMan will help you handle your list of attendees at an event, managing the list of registered persons and marking persons as present.

Main features:
- an admin (in the future: anyone) can create and manage new events
- events can define a registration form with many custom fields
- a person can join (or leave) an event, submitting the custom forms
- no registration is required to join/leave an event
- quickly mark a registered person as an attendee
- easy way to add a new person, if it's already known from a previous event or if it's a completely new person
- can import Eventbrite CSV export files
- RESTful interface that can be called by third-party applications (see the https://github.com/raspibo/event_man/ repository for a simple script that checks people in using a barcode/QR-code reader)
- ability to run triggers to respond to an event (e.g. when a person is marked as attending to an event)
- can run on HTTPS
- multiple workstations are kept in sync (i.e.: marking a person as an attendee is shown in every workstation currently viewing the list of persons registered at an event)

See the *screenshots* directory for some images.


Development
===========

See the *docs/DEVELOPMENT.md* file for more information about how to contribute.


Technological stack
===================

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

Be sure to have a running MongoDB server, locally. If you want to install the dependencies only locally to the current user, you can append the *--user* argument to the *pip* calls. Please also install the *python-dev* package, before running the following commands.

    wget https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install tornado # version 4.2 or later
    sudo pip install pymongo # version 3.2.2 or later
    sudo pip install pycups # only needed if you want to print labels
    git clone https://github.com/raspibo/eventman
    cd eventman
    ./eventman\_server.py --debug


Open browser and navigate to: http://localhost:5242/

If you store SSL key and certificate in the *ssl* directory (default names: eventman\_key.pem and eventman\_cert.pem), HTTPS will be used: https://localhost:5242/

Authentication
==============

By default, authentication is not required; unregistered and unprivileged users can see and join events, but are unable to edit or handle them. Administrator users can create ed edit events; more information about how permissions are handled can be found in the *docs/DEVELOPMENT.md* file.

The default administrator username and password are **admin** and **eventman**. If you want to force authentication, run the daemon with --authentication=on

Demo database
=============

In the *data/dumps/eventman\_test\_db.tar.gz* you can find a sample db with over 1000 fake persons and a couple of events to play with. Decompress it and use *mongorestore* to import it.


License and copyright
=====================

Copyright 2015-2016 Davide Alberani <da@erlug.linux.it>, RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

