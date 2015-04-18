Directory for scripts that will be executed when a given action is encoutered.

You have to put your scripts into {action}.d subdirectories; the scripts must be executable.

Valid actions:

- PUT /events/:event_id/persons/:person_id
  - update_person_in_event (update_person_in_event.d): called for each update
  - attends (attends.d): only called when a person is attending at an event


