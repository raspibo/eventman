'use strict';

/* Controllers; their method are available where specified with the ng-controller
 * directive or for a given route/state (see app.js).  They use some services to
 * connect to the backend (see services.js). */
var eventManControllers = angular.module('eventManControllers', []);


/* A controller that can be used to navigate. */
eventManControllers.controller('NavigationCtrl', ['$scope', '$rootScope', '$location', 'Setting', 'Info',
    function ($scope, $rootScope, $location, Setting, Info) {
        $scope.logo = {};

        $scope.getLocation = function() {
            return $location.absUrl();
        };

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
eventManControllers.controller('ModalConfirmInstanceCtrl', ['$scope', '$uibModalInstance', 'message',
    function ($scope, $uibModalInstance, message) {
        $scope.message = message;

        $scope.ok = function () {
            $uibModalInstance.close($scope);
        };

        $scope.cancel = function () {
            $uibModalInstance.dismiss('cancel');
        };
    }]
);


eventManControllers.controller('EventsListCtrl', ['$scope', 'Event', '$uibModal', '$log', '$translate', '$rootScope',
    function ($scope, Event, $uibModal, $log, $translate, $rootScope) {
        $scope.events = Event.all();
        $scope.eventsOrderProp = "-begin_date";

        $scope.confirm_delete = 'Do you really want to delete this event?';
        $rootScope.$on('$translateChangeSuccess', function () {
            $translate('Do you really want to delete this event?').then(function (translation) {
                $scope.confirm_delete = translation;
            });
        });

        $scope.remove = function(_id) {
            var modalInstance = $uibModal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                Event.remove({'id': _id}, function() {
                    $scope.events = Event.all();
                    }
                );
            });
        };
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', '$state', 'Event', '$log', '$translate', '$rootScope',
    function ($scope, $state, Event, $log, $translate, $rootScope) {
        $scope.event = {};
        $scope.event.persons = [];
        $scope.event.formSchema = {};
        $scope.eventFormDisabled = false;

        if ($state.params.id) {
            $scope.event = Event.get($state.params);
            if ($state.is('event.view') || !$rootScope.hasPermission('event|update')) {
                $scope.eventFormDisabled = true;
            }
        }

        // store a new Event or update an existing one
        $scope.save = function() {
                // avoid override of event.persons list.
                var this_event = angular.copy($scope.event);
                if (this_event.persons) {
                    delete this_event.persons;
                }
                if (this_event._id === undefined) {
                    $scope.event = Event.save(this_event);
                } else {
                    $scope.event = Event.update(this_event);
                }
                $scope.eventForm.$setPristine(false);
        };
    }]
);


eventManControllers.controller('EventTicketsCtrl', ['$scope', '$state', 'Event', 'EventTicket', 'Person', 'Setting', '$log', '$translate', '$rootScope', 'EventUpdates', '$uibModal',
    function ($scope, $state, Event, EventTicket, Person, Setting, $log, $translate, $rootScope, EventUpdates, $uibModal) {
        $scope.personsOrder = ["name", "surname"];
        $scope.countAttendees = 0;
        $scope.message = {};
        $scope.event = {};
        $scope.ticket = {};
        $scope.formSchema = {};
        $scope.formData = {};
        $scope.guiOptions = {dangerousActionsEnabled: false};
        $scope.customFields = Setting.query({setting: 'person_custom_field', in_event_details: true});

        $scope.formFieldsMap = {};
        $scope.formFieldsMapRev = {};

        if ($state.params.id) {
            $scope.event = Event.get({id: $state.params.id}, function(data) {
                $scope.$watchCollection(function() {
                        return $scope.event.persons;
                    }, function(prev, old) {
                        $scope.calcAttendees();
                    }
                );
                if (!(data && data.formSchema)) {
                    return;
                }
                $scope.formSchema = data.formSchema.edaFieldsModel;
                $scope.extractFormFields(data.formSchema.formlyFieldsModel);

                if ($state.params.ticket_id) {
                    EventTicket.get({id: $state.params.id, ticket_id: $state.params.ticket_id}, function(data) {
                        $scope.ticket = data;
                        angular.forEach(data, function(value, key) {
                            if (!$scope.formFieldsMapRev[key]) {
                                return;
                            }
                            $scope.formData[$scope.formFieldsMapRev[key]] = value;
                        });
                    });
                }

            });

            if ($state.is('event.tickets')) {
                $scope.allPersons = Person.all();

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
                        $log.debug('received ' + data.action + ' action from websocket source ' + data.uuid);
                        if ($rootScope.app_uuid == data.uuid) {
                            $log.debug('do not process our own message');
                            return false;
                        }
                        if (!$scope.event.persons) {
                            $scope.event.persons = [];
                        }
                        var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                                return data._id == el._id;
                        });
                        $log.debug(data);
                        if (person_idx != -1) {
                            $log.debug('_id ' + data._id + ' found');
                        } else {
                            $log.debug('_id ' + data._id + ' not found');
                        }

                        if (data.action == 'update' && person_idx != -1 && $scope.event.persons[person_idx] != data.person) {
                            $scope.event.persons[person_idx] = data.person;
                        } else if (data.action == 'add' && person_idx == -1) {
                            $scope._localAddTicket(data.person);
                        } else if (data.action == 'delete' && person_idx != -1) {
                            $scope._localRemoveAttendee({_id: data._id});
                        }
                    }
                );
            }
        }

        $scope.calcAttendees = function() {
            if (!($scope.event && $scope.event.persons)) {
                $scope.countAttendees = 0;
                return;
            }
            var attendees = 0;
            angular.forEach($scope.event.persons, function(value, key) {
                if (value.attended && !value.cancelled) {
                    attendees += 1;
                }
            });
            $scope.countAttendees = attendees;
        };

        /* Stuff to do when an attendee is added locally. */
        $scope._localAddTicket = function(person) {
            if (!$scope.event.persons) {
                $scope.event.persons = [];
            }
            var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                    return person._id == el._id;
            });
            if (person_idx != -1) {
                $log.debug('person already present: not added');
                return false;
            }
            $scope.event.persons.push(person);
        };

        $rootScope.$on('event.ticket.new', function(evt, ticket) {
            $scope._localAddTicket(ticket);
        });

        $rootScope.$on('event.ticket.update', function(evt, ticket) {
            if (!$scope.event.persons) {
                $scope.event.persons = [];
            }
            var ticket_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                    return ticket._id == el._id;
            });
            if (ticket_idx == -1) {
                $log.debug('person not present: not updated');
                return false;
            }
            $scope.event.persons[ticket_idx] = ticket;
        });

        $scope._addTicket = function(person) {
            person.event_id = $state.params.id;
            EventTicket.add(person, function() {
                $scope._localAddTicket(person);
            });
            $scope.query = '';
            return person;
        };

        $scope._setAttended = function(person) {
            $scope.setPersonAttribute(person, 'attended', true, function() {
                var all_person_idx = $scope.allPersons.findIndex(function(el, idx, array) {
                    return person._id == el._id;
                });
                if (all_person_idx != -1) {
                    $scope.allPersons.splice(all_person_idx, 1);
                }
            }, true);
        };

        $scope.fastAddAttendee = function(person) {
            $log.debug('EventDetailsCtrl.fastAddAttendee.person:');
            $log.debug(person);
            person = $scope._addTicket(angular.copy(person));
            $scope._setAttended(person);
        };

        $scope.setPersonAttribute = function(person, key, value, callback, hideMessage) {
            $log.debug('EventDetailsCtrl.setPersonAttribute.event_id: ' + $state.params.id);
            $log.debug('EventDetailsCtrl.setPersonAttribute._id: ' + person._id);
            $log.debug('EventDetailsCtrl.setPersonAttribute.key: ' + key + ' value: ' + value);
            var newData = {event_id: $state.params.id, _id: person._id};
            newData[key] = value;
            EventTicket.update(newData, function(data) {
                if (!(data && data._id && data.person)) {
                    return;
                }
                var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                    return data._id == el._id;
                });
                if (person_idx == -1) {
                    $log.warn('unable to find ticket _id ' + _id);
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
            if (!(person && person._id && $scope.event.persons)) {
                return;
            }
            var person_idx = $scope.event.persons.findIndex(function(el, idx, array) {
                return person._id == el._id;
            });
            if (person_idx == -1) {
                $log.warn('unable to find and delete ticket _id ' + person._id);
                return;
            }
            var removed_person = $scope.event.persons.splice(person_idx, 1);
            // to be used to populate allPersons, if needed.
            if (removed_person.length) {
                person = removed_person[0];
            }
            var all_person_idx = $scope.allPersons.findIndex(function(el, idx, array) {
                return person._id == el._id;
            });
            if (all_person_idx == -1 && person._id) {
                $scope.allPersons.push(person);
            }
        };

        $scope.removeAttendee = function(person) {
            EventTicket.delete({
                    event_id: $state.params.id,
                    ticket_id: person._id
                }, function() {
                    $scope._localRemoveAttendee(person);
            });
        };

        $scope.saveForm = function(easyFormGeneratorModel) {
            $scope.event.formSchema = easyFormGeneratorModel;
            $scope.save();
        };

        $scope.showMessage = function(cfg) {
            $scope.message.show(cfg);
        };

        $scope.extractFormFields = function(formlyFieldsModel) {
            if (!formlyFieldsModel) {
                return;
            }
            angular.forEach(formlyFieldsModel, function(row, idx) {
                if (!row.className == 'row') {
                    return;
                }
                angular.forEach(row.fieldGroup || [], function(item, idx) {
                    if (!(item.key && item.templateOptions && item.templateOptions.label)) {
                        return;
                    }
                    var value = item.templateOptions.label.toLowerCase();

                    $scope.formFieldsMap[item.key] = value;
                    $scope.formFieldsMapRev[value] = item.key;
                });
            });
        };

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
                        new_order.push(value);
                    }
                }
            );
            $scope.personsOrder = new_order;
        };

        $scope.openQuickAddTicket = function(_id) {
            var modalInstance = $uibModal.open({
                templateUrl: 'modal-quick-add-ticket.html',
                controller: 'EventTicketsCtrl'
            });
            modalInstance.result.then(function() {
            });
        };

        $scope.addTicket = function(person) {
            person.event_id = $state.params.id;
            EventTicket.add(person, function(ticket) {
                $log.debug(ticket);
                $rootScope.$emit('event.ticket.new', ticket);
                if (!$state.is('event.tickets')) {
                    $state.go('event.ticket.edit', {id: $scope.event._id, ticket_id: ticket._id});
                } else if ($scope.$close) {
                    $scope._setAttended(person);
                    $scope.$close();
                }
            });
        };

        $scope.updateTicket = function(ticket, cb) {
            ticket.event_id = $state.params.id;
            EventTicket.update(ticket, function(t) {
                $rootScope.$emit('event.ticket.update', ticket);
                if (cb) {
                    cb(t);
                }
            });
        };

        $scope.submitForm = function(dataModelSubmitted) {
            angular.forEach(dataModelSubmitted, function(value, key) {
                key = $scope.formFieldsMap[key] || key;
                $scope.ticket[key] = value;
            });
            if (!$state.params.ticket_id) {
                $scope.addTicket($scope.ticket);
            } else {
                $scope.updateTicket($scope.ticket);
            }
        };

        $scope.toggleTicket = function() {
            if (!$scope.ticket._id) {
                return;
            }
            $scope.ticket.cancelled = !$scope.ticket.cancelled;
            $scope.setPersonAttribute($scope.ticket, 'cancelled', $scope.ticket.cancelled, function() {
                $scope.guiOptions.dangerousActionsEnabled = false;
            });
        };

        $scope.cancelForm = function() {
            if (!$state.is('event.tickets')) {
                $state.go('events');
            } else if ($scope.$close) {
                $scope.$close();
            }
        };

        $scope.$on('$destroy', function() {
            $scope.EventUpdates && $scope.EventUpdates.close();
        });
    }]
);


eventManControllers.controller('PersonsListCtrl', ['$scope', 'Person', 'Setting', '$uibModal', '$translate', '$rootScope',
    function ($scope, Person, Setting, $uibModal, $translate, $rootScope) {
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
                        new_order.push(value);
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
            var modalInstance = $uibModal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                Person.remove({'id': _id}, function() {
                    $scope.persons = Person.all();
                    }
                );
            });
        };
    }]
);


eventManControllers.controller('PersonDetailsCtrl', ['$scope', '$state', 'Person', 'Event', 'Setting', '$log',
    function ($scope, $state, Person, Event, Setting, $log) {
        $scope.personsOrderProp = 'name';
        $scope.eventsOrderProp = '-begin_date';
        $scope.addToEvent = '';
        $scope.customFields = Setting.query({setting: 'person_custom_field',
            in_persons_list: true});

        if ($state.params.id) {
            $scope.person = Person.get($state.params);
            $scope.events = Person.getEvents({_id: $state.arams.id, all: true});
        } else {
            $scope.events = Event.all();
        }

        // store a new Person or update an existing one
        $scope.save = function() {
            if ($scope.person._id === undefined) {
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
            var attrs = {_id: evnt._id, person_id: $state.params.id};
            attrs[key] = value;
            Event.updatePerson(attrs,
                function(data) {
                    $scope.events = Person.getEvents({_id: $state.params.id, all: true});
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
                        $scope.events = Person.getEvents({_id: $state.params.id, all: true});
                    }
                );
            } else {
                Event.deletePerson({_id: evnt._id, person_id: person._id},
                    function(data) {
                        $scope.events = Person.getEvents({_id: $state.params.id, all: true});
                    }
                );
            }
        };
    }]
);


eventManControllers.controller('LoginCtrl', ['$scope', '$rootScope', '$state', '$log', 'User',
    function ($scope, $rootScope, $state, $log, User) {
        $scope.loginData = {};

        $scope.register = function() {
            User.add($scope.newUser, function(data) {
                $scope.login($scope.newUser);
            });
        };

        $scope.login = function(loginData) {
            if (!loginData) {
                loginData = $scope.loginData;
            }
            User.login(loginData, function(data) {
                if (!data.error) {
                    $rootScope.readInfo(function() {
                        $rootScope.clearError();
                        $state.go('events');
                    });
                }
            });
        };

        $scope.logout = function() {
            User.logout({}, function(data) {
                if (!data.error) {
                    $rootScope.readInfo(function() {
                        $state.go('events');
                    });
                }
            });
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

