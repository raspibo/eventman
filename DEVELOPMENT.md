Goals
=====

Definitions:
- **event**: a faire, convention, congress or any other kind of meeting
- **registered person**: someone who said it will attend at the event
- **attendee**: a person who actually *show up* at the event


Requirements:
- create a new event (**DONE**)
- create a new registered person manually (**DONE**)
- associate to an event a list of registered persons, creating them if needed (manually and importing from external sources)
- mark registered persons as present (including them in the list of attendees) (**DONE**)
- mark when an attendee enters/leaves the event
- execute actions when an attendee shows up or enters/leaves the event
- show information and statistics about registered persons, attendees and events


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
- /events/:event_id/persons/:person_id PUT - update the information about a person related to a given event (e.g.: if the person attended)
- /persons/:person_id/events GET - the list of events the person registered for
- /ebcsvpersons POST - csv file upload to import persons


Database layout
===============

Information are stored in MongoDB.  Whenever possible, object are converted
into integer, native ObjectId and datetime.

events collection
-----------------

Stores information about events and persons registered for a given event.

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
  - persons.$.email
  - persons.$.ebqrcode


persons collection
------------------

Basic information about a person:
- persons.name
- persons.surname
- persons.email


TODO
====

Next to be done
---------------

- easy way to add a new person to an event
- add the minimum required fields to lists and detailed pages for persons and events
- handle datetimes (on GUI with a calendar and on the backend deserializing ISO 8601 strings)
- modal on event/person removal

Nice to have
------------

- a test suite
- join the page used to add persons/events into the lists (shown when the filter field returns nothing and/or when a button is pressed)
- notifications for form editing and other actions
- authentication for administrators
- i18n
- logging and debugging code


