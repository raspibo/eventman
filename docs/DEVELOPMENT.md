Development
===========

Every contribution, in form of code or ideas, is welcome.


Definitions
===========

- **event**: a faire, convention, congress or any other kind of meeting
- **person**: everyone hates them
- **registered person**: someone who said will attend at the event
- **attendee**: a person who actually *show up* (is checked in) at the event
- **ticket**: an entry in the list of persons registered at an event (one ticket, one registered person)
- **user**: a logged in user of the EventMan(ager) web interface (not the same as "person")
- **trigger**: an action that will cause the execution of some scripts


Paths
=====

Webapp
------

These are the paths you see in the browser (AngularJS does client-side routing: no request is issued to the web server, during navigation, if not for fetching data and issuing commands):

- /#/events - the list of events
- /#/event/new - edit form to create a new event
- /#/event/:event\_id/edit - edit form to modify an existing event
- /#/event/:event\_id/view - show read-only information about an existing event
- /#/event/:event\_id/tickets - show the list of persons registered at the event
- /#/event/:event\_id/ticket/new - add a new ticket to an event
- /#/event/:event\_id/ticket/:ticket\_id/edit - edit an existing ticket
- /#/users - the list of users
- /#/user/:user\_id/edit - edit an existing user (contains the list of events the user registered for)
- /#/import/persons - form used to import persons in bulk
- /#/login - login and new user forms
- /logout - when visited, the user is logged out


Web server
----------

The paths used to communicate with the Tornado web server:

- /events GET  - return the list of events
- /events POST - store a new event
- /events/:event\_id GET    - return information about an existing event
- /events/:event\_id PUT    - update an existing event
- /events/:event\_id DELETE - delete an existing event
- /events/:event\_id/tickets GET  - return the complete list of tickets of the event
- /events/:event\_id/tickets POST - add a new ticket to this event
- /events/:event\_id/tickets/:ticket\_id GET    - return a ticket (e.g.: name, surname, ticket ID, ...)
- /events/:event\_id/tickets/:ticket\_id PUT    - update a ticket (e.g.: if the ticket attended)
- /events/:event\_id/tickets/:ticket\_id DELETE - remove the entry from the list of registered tickets
- /users GET  - list of users
- /users POST - create a new user
- /users/:user\_id PUT - update an existing user
- /settings GET - settings to customize the GUI (logo, extra columns for events and tickets lists)
- /info GET - information about the current user
- /ebcsvpersons POST - csv file upload to import persons
- /login POST - log a user in
- /logout GET - when visited, the user is logged out

Notice that the above paths are the ones used by the webapp. If you plan to use them from an external application (like the _event\_man_ barcode/qrcode scanner) you better prepend all the path with /v1.0, where 1.0 is the current value of API\_VERSION.
The main advantage of doing so is that, for every call, a useful status code and a JSON value is returned.

Also, remember that most of the paths can take query parameters that will be used as a filter, like GET /events/:event\_id/tickets?name=Mario


Permissions
===========

Being too lazy to implement a proper MAC or RBAC, we settled to a simpler mapping on CRUD operations on paths. This will probably change in the future.

User's permission are stored in the *permission* key, and merged with a set of defaults, valid also for unregistered users. Operations are *read*, *create*, *update* and *delete* (plus the spcial *all* value). There's also the special *admin|all* value: if present, the user has every privilege.

Permissions are strings: the path and the permission are separated by **|**; the path components (resource:sub-resource, if any) are separated by **:**. In case we are not accessing a specific sub-resource (i.e.: we don't have a sub-resource ID), the **-all** string is appended to the resource name. For example:
- **events|read**: ability to retrieve the list of events and their data (some fields, like the list of registered persons, are filtered out if you don't have other permissions)
- **event:tickets|all**: ability to do everything to a ticket (provided that you know its ID)
- **event:tickets-all|create**: ability to create a new ticket (you don't have an ID, if you're creating a new ticket, hence the -all suffix)


Triggers
========

Sometimes we have to execute one or more scripts in reaction to an action.

In the **data/triggers** we have a series of directories; scripts inside of them will be executed when the related action was performed on the GUI or calling the controller.

In the data/trigger directory you can create a directory named with this schema: *crudAction_document[_resource]*, where crudAction is one in "create", "update", "delete" (there're no triggers for "read"). So, for example you can create scripts in directories named:
- create\_user
- delete\_event
- update\_event\_tickets

We also have some special triggers, which will contain more information (for example: both the old and the new ticket, updating one):
- **update\_ticket\_in\_event**: executed every time a ticket in a given event is updated.
- **attends**: executed only when a person is marked as attending an event.

update\_ticket\_in\_event and attends will receive these information:
- via *environment*:
  - NAME
  - SURNAME
  - EMAIL
  - COMPANY
  - JOB
  - TICKET\_ID
  - EVENT\_ID
  - EVENT\_TITLE
  - SEQ
  - SEQ\_HEX
- via stdin, a dictionary containing:
  - dictionary **old** with the old data of the ticket
  - dictionary **new** with the new data of the ticket
  - dictionary **event** with the event information
  - boolean **merged**, true if the data was updated

In the **data/triggers-available** there is an example of script: **echo.py**.


Database layout
===============

Information are stored in MongoDB.  Whenever possible, object are converted into native ObjectId.

events collection
-----------------

Stores information about events and tickets.

Main field:

- title
- begin\_date
- begin\_time
- end\_date
- end\_time
- summary
- description
- where
- group\_id
- number\_of\_tickets
- ticket\_sales\_begin\_date
- ticket\_sales\_begin\_time
- ticket\_sales\_end\_date
- ticket\_sales\_end\_time
- tickets - a list of information about tickets (each entry is a ticket)
  - tickets.$.\_id
  - tickets.$.ticket\_id
  - tickets.$.attended
  - tickets.$.name
  - tickets.$.surname
  - tickets.$.email
  - tickets.$.company
  - tickets.$['job title']
  - tickets.$.ebqrcode
  - tickets.$.seq
  - tickets.$.seq\_hex

Notice that all the fields used to identiy a person (name, surname, email) depends on how you've edited the event's form.

users collection
----------------

Contains a list of username and associated values, like the password used for authentication.

To generate the hash, use:
    import utils
    print utils.hash\_password('MyVerySecretPassword')


Code layout
===========

The code is so divided:

    +- eventman_server.py - the Tornado Web server
    +- backend.py - stuff to interact with MongoDB
    +- utils.py - utilities
    +- angular_app/ - the client-side web application
    |  |
    |  +- *.html - AngularJS templates
    |  +- Gruntfile.js - Grunt file to extract i18n strings
    |  +- js/*.js - AngularJS code
    |     |
    |     +- app.js - main application and routing
    |     +- controllers.js - controllers of the templates
    |     +- services.js - interaction with the web server
    |     +- directives.js - stuff to interact with the DOM
    |     +- filters.js - filtering data
    |     +- i18n.js - i18n
    +- data/
    |  |
    |  +- triggers/
    |     |
    |     +- triggers-available/ - various trigger scripts
    |     +- triggers/ enabled trigger scripts
    |        |
    |        +- attends.d/ - scripts to be executed when a person is marked as an attendee
    |        +- create_ticket_in_event.d/ - scripts that are run when a ticket is created
    |        +- update_ticket_in_event.d/ - scripts that are run when a ticket is updated
    |        +- delete_ticket_in_event.d/ - scripts that are run when a ticket is deleted
    +- ssl/ - put here your eventman_cert.pem  and eventman_key.pem certs
    +- static/
    |  |
    |  +- js/ - every third-party libraries (plus eventman.js with some small utils)
    |  +- css/ - third-party CSS (plus eventman.css)
    |  +- fonts/ - third-party fonts
    |  +- images/ - third-party images
    |  +- i18n/ - i18n files
    +- templates/ - Tornado Web templates (not used)
    +- tests/ - eeeehhhh

Most of the time you have to edit something in angular\_app/js/ (for the logic; especially controllers.js and services.js), angular\_app/\*.html (for the presentation) or eventman\_server.py for the backend.

Dependency management and other hipster tools
---------------------------------------------

But, but, but... you don't use bower/npm/jam/CthulhuJS!

Yes, exactly. I'm too old for that stuff: I just downloaded the third-party libraries that I needed and put them in static/.  Seems to work, by the way.

I you're a big fan of those tools, please go ahead and send me a pull request.

Coding style and conventions
----------------------------

It's enough to be consistent within the document you're editing.

I suggest four spaces instead of tabs for all the code: Python (**mandatory**), JavaScript, HTML and CSS.

Python code documented following the [Sphinx](http://sphinx-doc.org/) syntax.

