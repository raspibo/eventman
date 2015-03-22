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
- mark registered persons as present (including them in the list of attendees)
- mark when an attendee enters/leaves the event
- execute actions when an attendee shows up or enters/leaves the event
- show information and statistics about registered persons, attendees and events


TODO
====

Next to be done
---------------

- ability to delete a person or event
- import persons from CSV
- introduce the concept of registered persons and attendees in the GUI and in the database
- add the minimum required fields to lists and detailed pages for persons and events


Nice to have
------------

- a test suite
- join the page used to add persons/events into the lists (shown when the filter field returns nothing and/or when a button is pressed)
- notifications for form editing and other actions


