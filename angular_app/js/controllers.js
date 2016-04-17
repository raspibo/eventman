'use strict';

/* Controllers; their method are available where specified with the ng-controller
 * directive or for a given route/state (see app.js).  They use some services to
 * connect to the backend (see services.js). */
var eventManControllers = angular.module('eventManControllers', []);


/* A controller that can be used to navigate. */
eventManControllers.controller('NavigationCtrl', ['$scope', '$location', 'Setting',
    function ($scope, $location, Setting) {
        $scope.logo = {};

        $scope.go = function(url) {
            $location.url(url);
        };

        Setting.query({setting: 'logo'}, function(data) {
            if (data && data.length) {
                $scope.logo = data[0];
            }
        });

        $scope.isActive = function(view) {
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


/* Controller for modals. */
eventManControllers.controller('ModalConfirmInstanceCtrl', ['$scope', '$modalInstance', 'message',
    function ($scope, $modalInstance, message) {
        $scope.message = message;

        $scope.ok = function () {
            $modalInstance.close($scope);
        };

        $scope.cancel = function () {
            $modalInstance.dismiss('cancel');
        };
    }]
);


eventManControllers.controller('EventsListCtrl', ['$scope', 'Event', '$modal', '$log', '$translate', '$rootScope',
    function ($scope, Event, $modal, $log, $translate, $rootScope) {
        $scope.events = Event.all();
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = "'-begin-date'";

        $scope.confirm_delete = 'Do you really want to delete this event?';
        $rootScope.$on('$translateChangeSuccess', function () {
            $translate('Do you really want to delete this event?').then(function (translation) {
                $scope.confirm_delete = translation;
            });
        });

        $scope.remove = function(_id) {
            var modalInstance = $modal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                console.debug('here');
                Event.remove({'id': _id}, function() {
                    $scope.events = Event.all();
                    }
                );
            });
        };
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', '$state', 'Event', 'Person', 'EventUpdates', '$stateParams', 'Setting', '$log', '$translate',
    function ($scope, $state, Event, Person, EventUpdates, $stateParams, Setting, $log, $translate) {
        $scope.personsOrder = ["name", "surname"];
        $scope.countAttendees = 0;
        $scope.message = {};
        $scope.event = {};
        $scope.event.persons = [];
        $scope.customFields = Setting.query({setting: 'person_custom_field', in_event_details: true});

        if ($stateParams.id) {
            $scope.event = Event.get($stateParams, function() {
                $scope.$watchCollection(function() {
                        return $scope.event.persons;
                    }, function(prev, old) {
                        $scope.calcAttendees();
                    }
                );
            });
            $scope.allPersons = Person.all();

            if ($state.is('event.info')) {
                // Handle WebSocket connection used to update the list of persons.
                $scope.EventUpdates = EventUpdates;
                $scope.EventUpdates.open();
                $scope.$watchCollection(function() {
                        return $scope.EventUpdates.data;
                    }, function(prev, old) {
                        if (!($scope.EventUpdates.data && $scope.EventUpdates.data.update)) {
                            return;
                        }
                        var data = $scope.EventUpdates.data.update;
                        $log.debug('received ' + data.action + ' action from websocket');
                        if (!$scope.event.persons) {
                            $scope.event.persons = [];
                        }
                        var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                                return data.person_id == el.person_id;
                        });
                        if (person_idx != -1) {
                            $log.debug('person_id ' + data.person_id + ' found');
                        } else {
                            $log.debug('person_id ' + data.person_id + ' not found');
                        }

                        if (data.action == 'update' && person_idx != -1 && $scope.event.persons[person_idx] != data.person) {
                            $scope.event.persons[person_idx] = data.person;
                        } else if (data.action == 'add' && person_idx == -1) {
                            $scope._localAddAttendee(data.person, true);
                        } else if (data.action == 'delete' && person_idx != -1) {
                            $scope._localRemoveAttendee({person_id: data.person_id});
                        }
                    }
                );
            }
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
                $scope.eventForm.$setPristine(false);
        };

        $scope.calcAttendees = function() {
            if (!($scope.event && $scope.event.persons)) {
                $scope.countAttendees = 0;
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

        /* Stuff to do when an attendee is added locally. */
        $scope._localAddAttendee = function(person, hideMessage) {
            if (!$scope.event.persons) {
                $scope.event.persons = [];
            }
            $scope.event.persons.push(person);
            $scope.setPersonAttribute(person, 'attended', true, function() {
                var all_person_idx = $scope.allPersons.findIndex(function(el, idx, array) {
                    return person.person_id == el.person_id;
                });
                if (all_person_idx != -1) {
                    $scope.allPersons.splice(all_person_idx, 1);
                }
            }, hideMessage);
        };

        $scope._addAttendee = function(person) {
            person.person_id = person._id;
            person._id = $stateParams.id;
            Event.addPerson(person, function() {
                $scope._localAddAttendee(person);
            });
            $scope.query = '';
        };

        $scope.fastAddAttendee = function(person, isNew) {
            $log.debug('EventDetailsCtrl.fastAddAttendee.person:');
            $log.debug(person);
            if (isNew) {
                var personObj = new Person(person);
                personObj.$save(function(p) {
                    $scope._addAttendee(angular.copy(p));
                    $scope.newPerson = {};
                });
            } else {
                $scope._addAttendee(angular.copy(person));
            }
        };

        $scope.setPersonAttribute = function(person, key, value, callback, hideMessage) {
            $log.debug('EventDetailsCtrl.setPersonAttribute.event_id: ' + $stateParams.id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.person_id: ' + person.person_id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.key: ' + key + ' value: ' + value);
            var data = {_id: $stateParams.id, person_id: person.person_id};
            data[key] = value;
            Event.updatePerson(data,
                function(data) {
                    if (!(data && data.person_id && data.person)) {
                        return;
                    }
                    var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                        return data.person_id == el.person_id;
                    });
                    if (person_idx == -1) {
                        $log.warn('unable to find person_id ' + person_id);
                        return;
                    }
                    if ($scope.event.persons[person_idx] != data.person) {
                        $scope.event.persons[person_idx] = data.person;
                    }
                    if (callback) {
                        callback(data);
                    }
                    if (key === 'attended' && !hideMessage) {
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

        /* Stuff to do when an attendee is removed locally. */
        $scope._localRemoveAttendee = function(person) {
            $log.debug('_localRemoveAttendee');
            $log.debug(person);
            if (!(person && person.person_id && $scope.event.persons)) {
                return;
            }
            var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                return person.person_id == el.person_id;
            });
            if (person_idx == -1) {
                $log.warn('unable to find and delete person_id ' + person.person_id);
                return;
            }
            $scope.event.persons.splice(person_idx, 1);
        };

        $scope.removeAttendee = function(person) {
            Event.deletePerson({
                    _id: $stateParams.id,
                    person_id: person.person_id
                }, function() {
                    $scope._localRemoveAttendee(person);
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


eventManControllers.controller('PersonsListCtrl', ['$scope', 'Person', 'Setting', '$modal', '$translate', '$rootScope',
    function ($scope, Person, Setting, $modal, $translate, $rootScope) {
        $scope.persons = Person.all();
        $scope.personsOrder = ["name", "surname"];
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_persons_list: true});

        $scope.confirm_delete = 'Do you really want to delete this person?';
        $rootScope.$on('$translateChangeSuccess', function () {
            $translate('Do you really want to delete this person?').then(function (translation) {
                $scope.confirm_delete = translation;
            });
        });

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

        $scope.setAttribute = function(person, key, value) {
            var data = {_id: person._id};
            data[key] = value;
            Person.update(data, function() {
                $scope.persons = Person.all();
            });
        };

        $scope.remove = function(_id) {
            var modalInstance = $modal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                console.debug('here');
                Person.remove({'id': _id}, function() {
                    $scope.persons = Person.all();
                    }
                );
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
            $scope.personForm.$setPristine(false);
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

