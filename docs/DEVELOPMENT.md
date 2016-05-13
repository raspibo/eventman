Goals
=====

Definitions:
- **event**: a faire, convention, congress or any other kind of meeting
- **registered person**: someone who said it will attend at the event
- **attendee**: a person who actually *show up* (checked in) at the event


Paths
=====

Webapp
------

These are the path you see in the browser (AngularJS does client-side routing: no request is issued to the web server, during navigation, if not for fetching data and issuing commands):

- /#/events - the list of events
- /#/event/new - edit form to create a new event
- /#/event/:event_id - show information about an existing event (contains the list of registered persons)
- /#/event/:event_id/edit - edit form to modify an existing event
- /#/persons - the list of persons
- /#/person/new - edit form to create a new person
- /#/person/:person_id - show information about an existing person (contains the list of events the person registered for)
- /#/person/:person_id/edit - edit form to modify an existing person
- /#/import/persons - form used to import persons in bulk
- /login - login form
- /logout - when visited, the user is logged out


Web server
----------

The paths used to communicate with the Tornado web server:

- /events GET  - return the list of events
- /events POST - store a new event
- /events/:event_id GET    - return information about an existing event
- /events/:event_id POST   - update an existing event
- /events/:event_id DELETE - delete an existing event
- /persons GET  - return the list of persons
- /persons POST - store a new person
- /persons/:person_id GET    - return information about an existing person
- /persons/:person_id POST   - update an existing person
- /persons/:person_id DELETE - delete an existing person
- /events/:event_id/persons GET - return the complete list of persons registered for the event
- /events/:event_id/persons/:person_id GET - return information about a person related to a given event (e.g.: name, surname, ticket ID, ...)
- /events/:event_id/persons/:person_id PUT - update the information about a person related to a given event (e.g.: if the person attended)
- /persons/:person_id/events GET - the list of events the person registered for
- /ebcsvpersons POST - csv file upload to import persons
- /login - login form
- /logout - when visited, the user is logged out

Notice that the above path are the ones used by the webapp. If you plan to use them from an external application (like the _eventman_ barcode/qrcode scanner) you better prepend all the path with /v1.0, where 1.0 is the current value of API\_VERSION.
The main advantage in doing so is that, for every call, a useful status code and a JSON value is returned (also for /v10/login that usually would show you the login page).

Also, remember that most of the paths can take query parameters that will be used as a filter, like GET /events/:event_id/persons?name=Mario


Triggers
========

Sometimes we have to execute some script in reaction to an event.

In the **data/triggers** we have a series of directories; scripts inside of them will be executed when the related action was performed on the GUI or calling the controller.

Available triggers:
- **update_person_in_event**: executed every time a person data in a given event is updated.
- **attends**: executed only when a person is marked as attending an event.

update_person_in_event and attends will receive these information:
- via *environment*:
  - NAME
  - SURNAME
  - EMAIL
  - COMPANY
  - JOB
  - PERSON_ID
  - EVENT_ID
  - EVENT_TITLE
  - SEQ
  - SEQ_HEX
- via stdin, a dictionary containing:
  - dictionary **old** with the old data of the person
  - dictionary **new** with the new data of the person
  - dictionary **event** with the event information
  - boolean **merged**, true if the data was updated

In the **data/triggers-available** there is an example of script: **echo.py**.

Database layout
===============

Information are stored in MongoDB.  Whenever possible, object are converted
into integer, native ObjectId and datetime.

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
- persons - a list of information about registered persons
  - persons.$.person_id
  - persons.$.attended
  - persons.$.name
  - persons.$.surname
  - persons.$.email
  - persons.$.company
  - persons.$.job
  - persons.$.ebqrcode
  - persons.$.seq
  - persons.$.seq_hex


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
    print utils.hash_password('MyVerySecretPassword')


Coding style and conventions
============================

It's enough to be consistent within the document you're editing.

I suggest four spaces instead of tabs for all the code: Python (**mandatory**), JavaScript, HTML and CSS.

Python code documented following the [Sphinx](http://sphinx-doc.org/) syntax.


TODO
====

Next to be done
---------------

- handle datetimes (on GUI with a calendar and on the backend deserializing ISO 8601 strings)
- modal on event/person removal

Nice to have
------------

- a test suite
- join the page used to add persons/events into the lists (shown when the filter field returns nothing and/or when a button is pressed)
- notifications for form editing and other actions
- authentication for administrators
- i18n
- settings page
- logging and debugging code

