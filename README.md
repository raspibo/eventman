Event Man(ager)
===============

Your friendly manager of attendees at an event.


Development
===========

See the DEVELOPMENT.md file for more information about how to contribute.


Technological stack
===================

- [AngularJS](https://angularjs.org/) (plus some third-party modules) for the webApp
- [Bootstrap](http://getbootstrap.com/) (plus [Angular UI](https://angular-ui.github.io/bootstrap/)) for the eye-candy
- [Tornado web](http://www.tornadoweb.org/) as web server
- [MongoDB](https://www.mongodb.org/) to store the data

The web part is incuded; you need to install Tornado, MongoDB and the pymongo module on your system (no configuration needed).


Coding style and conventions
============================

It's enough to be consistent within the document you're editing.

I suggest four spaces instead of tabs for all the code: Python (**mandatory**), JavaScript, HTML and CSS.

Python code documented following the [Sphinx](http://sphinx-doc.org/) syntax.


Install and run
===============

Be sure to have a running MongoDB server, locally.

    wget https://bootstrap.pypa.io/get-pip.py
    sudo python get-pip.py
    sudo pip install tornado
    sudo pip install pymongo
    cd
    git clone https://github.com/raspibo/eventman
    cd eventman
    ./eventman_server.py --debug


Open browser and navigate to: http://localhost:5242/


License and copyright
=====================

Copyright 2015 Davide Alberani <da@erlug.linux.it>  
               RaspiBO <info@raspibo.org>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

