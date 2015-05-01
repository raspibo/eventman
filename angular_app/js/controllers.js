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


eventManControllers.controller('EventDetailsCtrl', ['$scope', 'Event', 'Person', 'EventUpdates', '$stateParams', 'Setting', '$log',
    function ($scope, Event, Person, EventUpdates, $stateParams, Setting, $log) {
        $scope.personsOrder = ["name", "surname"];
        $scope.countAttendees = 0;
        $scope.message = {};
        $scope.event = {};
        $scope.event.persons = [];
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_event_details: true});

        if ($stateParams.id) {
            $scope.event = Event.get($stateParams, function() {
                $scope.$watchCollection(function() {
                        return $scope.event.persons;
                    }, function(prev, old) {
                        $scope.calcAttendees();
                    }
                );
            });

            // Handle WebSocket connection used to update the list of persons.
            $scope.EventUpdates = EventUpdates;
            $scope.EventUpdates.open();
            $scope.$watchCollection(function() {
                    return $scope.EventUpdates.data;
                }, function(prev, old) {
                    if (!($scope.EventUpdates.data && $scope.EventUpdates.data.persons)) {
                        return;
                    }
                    $scope.event.persons = $scope.EventUpdates.data.persons;
                }
            );
            $scope.allPersons = Person.all();
        }

        $scope.updateOrded = function(key) {
            var new_order = [key];
            var inv_key;
            if (key && key[0] === '-') {
                inv_key = key.substring(1);
            } else {
                inv_key = '-' + key;
            }
            angular.forEach($scope.personsOrder,
                function(value, idx) {
                    if (value !== key && value !== inv_key) {
                        new_order.push(value)
                    }
                }
            );
            $scope.personsOrder = new_order;
        };

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
            angular.forEach($scope.event.persons, function(value, key) {
                if (value.attended) {
                    attendees += 1;
                }
            });
            $scope.countAttendees = attendees;
        };

        $scope._addPerson = function(person_data) {
            var original_data = angular.copy(person_data);
            person_data.person_id = person_data._id;
            person_data._id = $stateParams.id;
            Event.addPerson(person_data, function() {
                // This could be improved adding it only locally.
                //$scope.event.persons.push(person_data);
                $scope.setPersonAttribute(person_data, 'attended', true, function() {
                    Event.get($stateParams, function(data) {
                        $scope.event.persons = angular.fromJson(data).persons;
                    });
                    var idx = $scope.allPersons.indexOf(original_data);
                    if (idx != -1) {
                        $scope.allPersons.splice(idx, 1);
                    } else {
                        $scope.allPersons = Person.all();
                    }
                    $scope.newPerson = {};
                    // XXX: must be converted in a i18n-able form.
                    var msg = '' + person_data.name + ' ' + person_data.surname + ' successfully added to event ' + $scope.event.title;
                    $scope.showMessage({message: msg});
                });
            });
            $scope.query = '';
        };

        $scope.fastAddPerson = function(person, isNew) {
            $log.debug('EventDetailsCtrl.fastAddPerson.person:');
            $log.debug(person);
            if (isNew) {
                var personObj = new Person(person);
                personObj.$save(function(p) {
                    $scope._addPerson(angular.copy(p));
                });
            } else {
                $scope._addPerson(angular.copy(person));
            }
        };

        $scope.setPersonAttribute = function(person, key, value, callback) {
            $log.debug('EventDetailsCtrl.setPersonAttribute.event_id: ' + $stateParams.id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.person_id: ' + person.person_id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.key: ' + key + ' value: ' + value);
            var data = {_id: $stateParams.id, person_id: person.person_id};
            data[key] = value;
            Event.updatePerson(data,
                function(data) {
                    $scope.event.persons = data;
                    if (callback) {
                        callback(data);
                    }
                    if (key === 'attended') {
                        var msg = {};
                        if (value) {
                            msg.message = '' + person.name + ' ' + person.surname + ' successfully added to event ' + $scope.event.title;
                        } else {
                            msg.message = '' + person.name + ' ' + person.surname + ' successfully removed from event ' + $scope.event.title;
                            msg.isError = true;
                        }
                        $scope.showMessage(msg);
                    }
            });
        };

        $scope.setPersonAttributeAndRefocus = function(person, key, value) {
            $scope.setPersonAttribute(person, key, value);
            $scope.query = '';
        };

        $scope.removeAttendee = function(person) {
            Event.deletePerson({
                    _id: $stateParams.id,
                    person_id: person.person_id
                },
                function(data) {
                    $scope.event.persons = data;
                    $scope.allPersons = Person.all();
            });
        };

        $scope.showMessage = function(cfg) {
            $scope.message.show(cfg);
        };

        $scope.$on('$destroy', function() {
            $scope.EventUpdates && $scope.EventUpdates.close();
        });
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
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_persons_list: true});

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
                        Event.addPerson(data);
                    }
                });
            } else {
                $scope.person = Person.update($scope.person, function(data) {
                    if ($scope.addToEvent) {
                        var data = angular.copy($scope.person);
                        data._id = $scope.addToEvent;
                        data.person_id = $scope.person._id;
                        data.attended = false;
                        Event.addPerson(data);
                    }
                });
            }
            $scope.personForm.$dirty = false;
        };

        $scope.setPersonAttributeAtEvent = function(evnt, key, value) {
            var attrs = {_id: evnt._id, person_id: $stateParams.id};
            attrs[key] = value;
            Event.updatePerson(attrs,
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
                Event.addPerson(data,
                    function(data) {
                        $scope.events = Person.getEvents({_id: $stateParams.id, all: true});
                    }
                );
            } else {
                Event.deletePerson({_id: evnt._id, person_id: person._id},
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

