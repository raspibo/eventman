'use strict';

/* Controllers; their method are available where specified with the ng-controller
 * directive or for a given route/state (see app.js).  They use some services to
 * connect to the backend (see services.js). */
var eventManControllers = angular.module('eventManControllers', []);


/* A controller that can be used to navigate. */
eventManControllers.controller('NavigationCtrl', ['$location',
    function ($location) {
        this.go = function(url) {
            $location.url(url);
        };

        this.isActive = function (view) { 
            if (view === $location.path()) {
                return true;
            }
            if (view[view.length-1] !== '/') {
                view = view + '/';
            }
            return $location.path().indexOf(view) == 0;
        };
    }]
);


/* Controller for a group of date and time pickers. */
eventManControllers.controller('DatetimePickerCtrl', ['$scope',
    function ($scope) {
        $scope.open = function($event) {
            $event.preventDefault();
            $event.stopPropagation();
            $scope.opened = true;
        };
    }]
);


eventManControllers.controller('EventsListCtrl', ['$scope', 'Event',
    function ($scope, Event) {
        $scope.events = Event.all();
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = "'-begin-date'";

        $scope.remove = function(_id) {
            Event.remove({'id': _id}, function() {
                $scope.events = Event.all();
            });
        };
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', 'Event', 'Person', '$stateParams', 'Setting', '$log',
    function ($scope, Event, Person, $stateParams, Setting, $log) {
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = '-begin-date';
        $scope.countAttendees = 0;
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_event_details: true});

        if ($stateParams.id) {
            $scope.event = Event.get($stateParams, function() {
                $scope.$watchCollection(function() {
                        return $scope.event.persons;
                    }, function(prev, old) {
                        $scope.calcAttendees();
                    });
            });
            $scope.allPersons = Person.all();
        }

        // store a new Event or update an existing one
        $scope.save = function() {
                // avoid override of event.persons list.
                var this_event = angular.copy($scope.event);
                if (this_event.persons) {
                    delete this_event.persons;
                }
                if (this_event.id === undefined) {
                    $scope.event = Event.save(this_event);
                } else {
                    $scope.event = Event.update(this_event);
                }
                $scope.eventForm.$dirty = false;
        };

        $scope.calcAttendees = function() {
            if (!($scope.event && $scope.event.persons)) {
                return;
            }
            var attendees = 0;
            $log.info($scope.event.persons.length);
            angular.forEach($scope.event.persons, function(value, key) {
                if (value.attended) {
                    attendees += 1;
                }
            });
            $scope.countAttendees = attendees;
        };

        $scope._addAttendee = function(person_data) {
            person_data.person_id = person_data._id;
            person_data._id = $stateParams.id;
            person_data.attended = true;
            Event.addAttendee(person_data, function() {
                $scope.event = Event.get($stateParams);
                $scope.allPersons = Person.all();
                $scope.newPerson = {};
            });
        };

        $scope.fastAddPerson = function(person, isNew) {
            $log.debug('EventDetailsCtrl.fastAddPerson.person:');
            $log.debug(person);
            if (isNew) {
                var personObj = new Person(person);
                personObj.$save(function(p) {
                    $scope._addAttendee(angular.copy(p));
                });
            } else {
                $scope._addAttendee(angular.copy(person));
            }
        };

        $scope.setAttribute = function(person, key, value) {
            var data = {_id: person._id};
            data[key] = value;
            Person.update(data, function() {
                $scope.persons = Person.all();
            });
        };

        $scope.setPersonAttribute = function(person, key, value) {
            $log.debug('EventDetailsCtrl.setPersonAttribute.event_id: ' + $stateParams.id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.person_id: ' + person.person_id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.key: ' + key + ' value: ' + value);
            var data = {_id: $stateParams.id, person_id: person.person_id};
            data[key] = value;
            Event.personAttended(data,
                function(data) {
                    $log.debug('EventDetailsCtrl.setPersonAttribute.data');
                    $log.debug(data);
                    $scope.event.persons = data;
            });
        };

        $scope.updateAttendee = function(person, attended) {
            $log.debug('EventDetailsCtrl.event_id: ' + $stateParams.id);
            $log.debug('EventDetailsCtrl.person_id: ' + person.person_id);
            $log.debug('EventDetailsCtrl.attended: ' + attended);
            Event.personAttended({
                    _id: $stateParams.id,
                    person_id: person.person_id,
                    'attended': attended
                },
                function(data) {
                    $log.debug('EventDetailsCtrl.personAttended.data');
                    $log.debug(data);
                    $scope.event.persons = data;
            });
        };

        $scope.removeAttendee = function(person) {
            Event.deleteAttendee({
                    _id: $stateParams.id,
                    person_id: person.person_id
                },
                function(data) {
                    $scope.event.persons = data;
                    $scope.allPersons = Person.all();
            });
        };
    }]
);


eventManControllers.controller('PersonsListCtrl', ['$scope', 'Person', 'Setting',
    function ($scope, Person, Setting) {
        $scope.persons = Person.all();
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = '-begin-date';
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_persons_list: true});

        $scope.setAttribute = function(person, key, value) {
            var data = {_id: person._id};
            data[key] = value;
            Person.update(data, function() {
                $scope.persons = Person.all();
            });
        };

        $scope.remove = function(_id) {
            Person.remove({'id': _id}, function() {
                $scope.persons = Person.all();
            });
        };
    }]
);


eventManControllers.controller('PersonDetailsCtrl', ['$scope', '$stateParams', 'Person', 'Event', 'Setting', '$log',
    function ($scope, $stateParams, Person, Event, Setting, $log) {
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = '-begin-date';
        $scope.addToEvent = '';
        $scope.customFields = Setting.query({setting: 'person_custom_field'});

        if ($stateParams.id) {
            $scope.person = Person.get($stateParams);
            $scope.events = Person.getEvents({_id: $stateParams.id, all: true});
        } else {
            $scope.events = Event.all();
        }
        // store a new Person or update an existing one
        $scope.save = function() {
            if ($scope.person.id === undefined) {
                $scope.person = new Person($scope.person);
                $scope.person.$save(function(person) {
                    if ($scope.addToEvent) {
                        var data = angular.copy(person);
                        data.person_id = data._id;
                        data._id = $scope.addToEvent;
                        data.attended = false;
                        Event.addAttendee(data);
                    }
                });
            } else {
                $scope.person = Person.update($scope.person, function(data) {
                    if ($scope.addToEvent) {
                        var data = angular.copy($scope.person);
                        data._id = $scope.addToEvent;
                        data.person_id = $scope.person._id;
                        data.attended = false;
                        Event.addAttendee(data);
                    }
                });
            }
            $scope.personForm.$dirty = false;
        };

        $scope.updateAttendee = function(event, attended) {
            $log.debug('PersonDetailsCtrl.event_id: ' + $stateParams.id);
            $log.debug('PersonDetailsCtrl.event_id: ' + event.event_id);
            $log.debug('PersonDetailsCtrl.attended: ' + attended);
            Event.personAttended({
                    _id: event._id,
                    person_id: $stateParams.id,
                    'attended': attended
                },
                function(data) {
                    $scope.events = Person.getEvents({_id: $stateParams.id, all: true});
                }
            );
        };

        $scope.switchRegistered = function(evnt, person, add) {
            $log.debug('PersonDetailsCtrl.switchRegistered.event_id: ' + evnt._id);
            $log.debug('PersonDetailsCtrl.switchRegistered.person_id: ' + person._id);
            $log.debug('PersonDetailsCtrl.switchRegistered.add: ' + add);
            if (add) {
                var data = angular.copy(person);
                data._id = evnt._id;
                data.person_id = person._id;
                data.attended = false;
                Event.addAttendee(data,
                    function(data) {
                        $scope.events = Person.getEvents({_id: $stateParams.id, all: true});
                    }
                );
            } else {
                Event.deleteAttendee({_id: evnt._id, person_id: person._id},
                    function(data) {
                        $scope.events = Person.getEvents({_id: $stateParams.id, all: true});
                    }
                );
            }
        };
    }]
);


eventManControllers.controller('FileUploadCtrl', ['$scope', '$log', '$upload', 'Event',
    function ($scope, $log, $upload, Event) {
            $scope.file = null;
            $scope.reply = {};
            $scope.events = Event.all();
            $scope.upload = function(file, url) {
                $log.debug("FileUploadCtrl.upload");
                $upload.upload({
                    url: url,
                    file: file,
                    fields: {targetEvent: $scope.targetEvent}
                }).progress(function(evt) {
                    var progressPercentage = parseInt(100.0 * evt.loaded / evt.total);
                    $log.debug('progress: ' + progressPercentage + '%');
                }).success(function(data, status, headers, config) {
                    $scope.file = null;
                    $scope.reply = angular.fromJson(data);
                });
            };
    }]
);

