Development
===========

As of June 2016, Event Man(ager) is under heavy refactoring. For a list of main changes that will be introduced, see https://github.com/raspibo/eventman/issues

Every contribution, in form of code or ideas, is welcome.


Definitions
===========

- **event**: a faire, convention, congress or any other kind of meeting
- **person**: everyone hates them
- **registered person**: someone who said will attend at the event
- **attendee**: a person who actually *show up* (is checked in) at the event
- **ticket**: an entry in the list of persons registered at an event
- **user**: a logged in user of th Event Man web interface (not the same as "person")
- **trigger**: an action that will run the execution of some scripts


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
- /#/persons - the list of persons
- /#/person/new - edit form to create a new person
- /#/person/:person\_id - show information about an existing person (contains the list of events the person registered for)
- /#/person/:person\_id/edit - edit form to modify an existing person
- /#/import/persons - form used to import persons in bulk
- /#/login - login form
- /logout - when visited, the user is logged out


Web server
----------

The paths used to communicate with the Tornado web server:

- /events GET  - return the list of events
- /events POST - store a new event
- /events/:event\_id GET    - return information about an existing event
- /events/:event\_id PUT    - update an existing event
- /events/:event\_id DELETE - delete an existing event
- /events/:event\_id/persons GET  - return the complete list of persons registered for the event
- /events/:event\_id/persons POST - insert a person in the list of registered persons of an event
- /events/:event\_id/persons/:person\_id GET    - return information about a person related to a given event (e.g.: name, surname, ticket ID, ...)
- /events/:event\_id/persons/:person\_id PUT    - update the information about a person related to a given event (e.g.: if the person attended)
- /events/:event\_id/persons/:person\_id DELETE - remove the entry from the list of registered persons
- /events/:event\_id/tickets GET  - return the complete list of tickets registered for the event
- /events/:event\_id/tickets POST - insert a person in the list of registered tickets of an event
- /events/:event\_id/tickets/:ticket\_id GET    - return information about a person related to a given event (e.g.: name, surname, ticket ID, ...)
- /events/:event\_id/tickets/:ticket\_id PUT    - update the information about a person related to a given event (e.g.: if the person attended)
- /persons GET  - return the list of persons
- /persons POST - store a new person
- /persons/:person\_id GET    - return information about an existing person
- /persons/:person\_id PUT    - update an existing person
- /persons/:person\_id DELETE - delete an existing person
- /persons/:person\_id/events GET - the list of events the person registered for
- /ebcsvpersons POST - csv file upload to import persons
- /users GET - list of users
- /users/:user\_id PUT - update an existing user
- /settings - settings to customize the GUI (logo, extra columns for events and persons lists)
- /info - information about the current user
- /login - login form
- /logout - when visited, the user is logged out

Notice that the above paths are the ones used by the webapp. If you plan to use them from an external application (like the _event\_man_ barcode/qrcode scanner) you better prepend all the path with /v1.0, where 1.0 is the current value of API\_VERSION.
The main advantage of doing so is that, for every call, a useful status code and a JSON value is returned.

Also, remember that most of the paths can take query parameters that will be used as a filter, like GET /events/:event\_id/persons?name=Mario

You have probably noticed that the /events/:event\_id/persons/\* and /events/:event\_id/tickets/\* paths seems to do the same thing. That's mostly true, and if we're talking about the data structure they are indeed the same (i.e.: a GET to /events/:event\_id/tickets/:ticket\_id will return the same {"person": {"name": "Mario", [...]}} structure as a call to /events/:event\_id/persons/:person\_id). The main difference is that the first works on the \_id property of the entry, the other on person\_id. Plus, the input and output are filtered in a different way, for example to prevent a registered person to autonomously set the attendee status or getting the complete list of registered persons.

Beware that most probably the /persons and /events/:event\_id/persons paths will be removed from a future version of Event Man(mager) in an attempt to rationalize how we handle data.


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

Available triggers:
- **update\_person\_in\_event**: executed every time a person data in a given event is updated.
- **attends**: executed only when a person is marked as attending an event.

update\_person\_in\_event and attends will receive these information:
- via *environment*:
  - NAME
  - SURNAME
  - EMAIL
  - COMPANY
  - JOB
  - PERSON\_ID
  - EVENT\_ID
  - EVENT\_TITLE
  - SEQ
  - SEQ\_HEX
- via stdin, a dictionary containing:
  - dictionary **old** with the old data of the person
  - dictionary **new** with the new data of the person
  - dictionary **event** with the event information
  - boolean **merged**, true if the data was updated

In the **data/triggers-available** there is an example of script: **echo.py**.


Database layout
===============

Information are stored in MongoDB.  Whenever possible, object are converted into integer, native ObjectId and datetime.

events collection
-----------------

Stores information about events and persons registered for a given event.

Please notice that information about a person registered for a given event is solely taken from the event.persons entry, and not to the relative entry in the persons collection. This may change in the future (to integrate missing information), but in general it is correct that, editing (or deleting) a person, older information about the partecipation to an event is not changed.

Main field:

- title
- begin-data
- begin-time
- end-date
- end-time
- persons - a list of information about registered persons (each entry is a ticket)
  - persons.$.\_id
  - persons.$.person\_id
  - persons.$.attended
  - persons.$.name
  - persons.$.surname
  - persons.$.email
  - persons.$.company
  - persons.$.job
  - persons.$.ebqrcode
  - persons.$.seq
  - persons.$.seq\_hex


persons collection
------------------

Basic information about a person:
- persons.name
- persons.surname
- persons.email
- persons.company
- persons.job


users collection
----------------

Contains a list of username and associated values, like the password used for authentication.

To generate the hash, use:
    import utils
    print utils.hash\_password('MyVerySecretPassword')


Coding style and conventions
============================

It's enough to be consistent within the document you're editing.

I suggest four spaces instead of tabs for all the code: Python (**mandatory**), JavaScript, HTML and CSS.

Python code documented following the [Sphinx](http://sphinx-doc.org/) syntax.

