'use strict';

/* Controllers; their method are available where specified with the ng-controller
 * directive or for a given route/state (see app.js).  They use some services to
 * connect to the backend (see services.js). */
var eventManControllers = angular.module('eventManControllers', []);


/* A controller that can be used to navigate. */
eventManControllers.controller('NavigationCtrl', ['$scope', '$rootScope', '$location', 'Setting', '$state',
    function ($scope, $rootScope, $location, Setting, $state) {
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


eventManControllers.controller('EventsListCtrl', ['$scope', 'Event', '$uibModal', '$log', '$translate', '$rootScope', '$state',
    function ($scope, Event, $uibModal, $log, $translate, $rootScope, $state) {
        $scope.tickets = [];
        $scope.events = Event.all(function(events) {
            if (events && $state.is('tickets')) {
                angular.forEach(events, function(evt, idx) {
                    var evt_tickets = (evt.tickets || []).slice(0);
                    angular.forEach(evt_tickets, function(obj, obj_idx) {
                        obj.event_title = evt.title;
                        obj.event_id = evt._id;
                    });
                    $scope.tickets.push.apply($scope.tickets, evt_tickets || []);
                });
            }
        });
        $scope.eventsOrderProp = "-begin_date";
        $scope.ticketsOrderProp = ["name", "surname"];

        $scope.confirm_delete = 'Do you really want to delete this event?';
        $rootScope.$on('$translateChangeSuccess', function () {
            $translate('Do you really want to delete this event?').then(function (translation) {
                $scope.confirm_delete = translation;
            });
        });

        $scope.deleteEvent = function(_id) {
            var modalInstance = $uibModal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                Event.delete({'id': _id}, function() {
                    $scope.events = Event.all();
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
            angular.forEach($scope.ticketsOrderProp,
                function(value, idx) {
                    if (value !== key && value !== inv_key) {
                        new_order.push(value);
                    }
                }
            );
            $scope.ticketsOrderProp = new_order;
        };

    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', '$state', 'Event', '$log', '$translate', '$rootScope',
    function ($scope, $state, Event, $log, $translate, $rootScope) {
        $scope.event = {};
        $scope.event.tickets = [];
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
                // avoid override of event.tickets list.
                var this_event = angular.copy($scope.event);
                if (this_event.tickets) {
                    delete this_event.tickets;
                }
                if (this_event._id === undefined) {
                    $scope.event = Event.save(this_event);
                } else {
                    $scope.event = Event.update(this_event);
                }
                $scope.eventForm.$setPristine(false);
        };

        $scope.saveForm = function(easyFormGeneratorModel) {
            $scope.event.formSchema = easyFormGeneratorModel;
            $scope.save();
        };
    }]
);


eventManControllers.controller('EventTicketsCtrl', ['$scope', '$state', 'Event', 'EventTicket', 'Setting', '$log', '$translate', '$rootScope', 'EventUpdates', '$uibModal',
    function ($scope, $state, Event, EventTicket, Setting, $log, $translate, $rootScope, EventUpdates, $uibModal) {
        $scope.ticketsOrder = ["name", "surname"];
        $scope.countAttendees = 0;
        $scope.message = {};
        $scope.event = {};
        $scope.event.tickets = [];
        $scope.ticket = {}; // current ticket, for the event.ticket.* states
        $scope.tickets = []; // list of all tickets, for the 'tickets' state
        $scope.formSchema = {};
        $scope.formData = {};
        $scope.guiOptions = {dangerousActionsEnabled: false};
        $scope.customFields = Setting.query({setting: 'ticket_custom_field', in_event_details: true});
        $scope.registeredFilterOptions = {all: true};

        $scope.formFieldsMap = {};
        $scope.formFieldsMapRev = {};

        if ($state.params.id) {
            $scope.event = Event.get({id: $state.params.id}, function(data) {
                $scope.$watchCollection(function() {
                        return $scope.event.tickets;
                    }, function(new_collection, old_collection) {
                        $scope.calcAttendees();
                    }
                );

                if (!(data && data.formSchema)) {
                    return;
                }
                $scope.formSchema = data.formSchema.edaFieldsModel;
                $scope.extractFormFields(data.formSchema.formlyFieldsModel);

                // Editing an existing ticket
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

            // Managing the list of tickets.
            if ($state.is('event.tickets')) {
                $scope.allPersons = Event.group_persons({id: $state.params.id});

                // Handle WebSocket connection used to update the list of tickets.
                $scope.EventUpdates = EventUpdates;
                $scope.EventUpdates.open();
                $scope.$watchCollection(function() {
                        return $scope.EventUpdates.data;
                    }, function(new_collection, old_collection) {
                        if (!($scope.EventUpdates.data && $scope.EventUpdates.data.update)) {
                            return;
                        }
                        var data = $scope.EventUpdates.data.update;
                        $log.debug('received ' + data.action + ' action from websocket source ' + data.uuid);
                        if ($rootScope.app_uuid == data.uuid) {
                            $log.debug('do not process our own message');
                            return false;
                        }
                        if (!$scope.event.tickets) {
                            $scope.event.tickets = [];
                        }
                        var ticket_idx = $scope.event.tickets.findIndex(function(el, idx, array) {
                            return data._id == el._id;
                        });
                        if (ticket_idx != -1) {
                            $log.debug('_id ' + data._id + ' found');
                        } else {
                            $log.debug('_id ' + data._id + ' not found');
                        }

                        if (data.action == 'update' && ticket_idx != -1 && $scope.event.tickets[ticket_idx] != data.ticket) {
                            $scope.event.tickets[ticket_idx] = data.ticket;
                        } else if (data.action == 'add' && ticket_idx == -1) {
                            $scope._localAddTicket(data.ticket);
                        } else if (data.action == 'delete' && ticket_idx != -1) {
                            $scope._localRemoveTicket({_id: data._id});
                        }
                    }
                );
            }
        } else if ($state.is('tickets')) {
            $scope.tickets = EventTicket.all();
        }

        $scope.calcAttendees = function() {
            if (!($scope.event && $scope.event.tickets)) {
                $scope.countAttendees = 0;
                return;
            }
            var attendees = 0;
            angular.forEach($scope.event.tickets, function(value, key) {
                if (value.attended && !value.cancelled) {
                    attendees += 1;
                }
            });
            $scope.countAttendees = attendees;
        };

        /* Stuff to do when a ticket is added, modified or removed locally. */

        $scope._localAddTicket = function(ticket, original_ticket) {
            if (!$state.is('event.tickets')) {
                return true;
            }
            var ret = true;
            if (!$scope.event.tickets) {
                $scope.event.tickets = [];
            }
            var ticket_idx = $scope.event.tickets.findIndex(function(el, idx, array) {
                return ticket._id == el._id;
            });
            if (ticket_idx != -1) {
                $log.warn('ticket already present: not added');
                ret = false;
            } else {
                $scope.event.tickets.push(ticket);
            }

            // Try to remove this person from the allPersons list using ID of the original entry or email.
            var field = null;
            var field_value = null;
            if (original_ticket && original_ticket._id) {
                field = '_id';
                field_value = original_ticket._id;
            } else if (ticket.email) {
                field = 'email';
                field_value = ticket.email;
            }
            if (field) {
                var all_person_idx = $scope.allPersons.findIndex(function(el, idx, array) {
                    return field_value == el[field];
                });
                if (all_person_idx != -1) {
                    $scope.allPersons.splice(all_person_idx, 1);
                }
            }
            return ret;
        };

        $scope._localUpdateTicket = function(ticket) {
            if (!$state.is('event.tickets')) {
                return;
            }
            if (!$scope.event.tickets) {
                $scope.event.tickets = [];
            }
            var ticket_idx = $scope.event.tickets.findIndex(function(el, idx, array) {
                return ticket._id == el._id;
            });
            if (ticket_idx == -1) {
                $log.warn('ticket not present: not updated');
                return false;
            }
            $scope.event.tickets[ticket_idx] = ticket;
        };

        $scope._localRemoveTicket = function(ticket) {
            if (!(ticket && ticket._id && $scope.event.tickets)) {
                return;
            }
            var ticket_idx = $scope.event.tickets.findIndex(function(el, idx, array) {
                return ticket._id == el._id;
            });
            if (ticket_idx == -1) {
                $log.warn('unable to find and delete ticket _id ' + ticket._id);
                return;
            }
            var removed_person = $scope.event.tickets.splice(ticket_idx, 1);
            // to be used to populate allPersons, if needed.
            var person = null;
            if (removed_person.length) {
                person = removed_person[0];
            } else {
                return;
            }
            if (!$scope.allPersons) {
                $scope.allPersons = [];
            }
            var all_person_idx = $scope.allPersons.findIndex(function(el, idx, array) {
                return person._id == el._id;
            });
            if (all_person_idx == -1 && person._id) {
                $scope.allPersons.push(person);
            }
        };

        $scope.setTicketAttribute = function(ticket, key, value, callback, hideMessage) {
            $log.debug('setTicketAttribute for _id ' + ticket._id + ' key: ' + key + ' value: ' + value);
            var newData = {event_id: $state.params.id, _id: ticket._id};
            newData[key] = value;
            EventTicket.update(newData, function(data) {
                if (!(data && data._id && data.ticket)) {
                    return;
                }
                if (callback) {
                    callback(data);
                }
                if (!$state.is('event.tickets')) {
                    return;
                }
                var ticket_idx = $scope.event.tickets.findIndex(function(el, idx, array) {
                    return data._id == el._id;
                });
                if (ticket_idx == -1) {
                    $log.warn('unable to find ticket _id ' + data._id);
                    return;
                }
                if ($scope.event.tickets[ticket_idx] != data.ticket) {
                    $scope.event.tickets[ticket_idx] = data.ticket;
                }
                if (key === 'attended' && !hideMessage) {
                    var msg = {};
                    if (value) {
                        msg.message = '' + ticket.name + ' ' + ticket.surname + ' successfully added to event ' + $scope.event.title;
                    } else {
                        msg.message = '' + ticket.name + ' ' + ticket.surname + ' successfully removed from event ' + $scope.event.title;
                        msg.isError = true;
                    }
                    $scope.showMessage(msg);
                }
            });
        };

        $scope.setTicketAttributeAndRefocus = function(ticket, key, value) {
            $scope.setTicketAttribute(ticket, key, value);
            $scope.query = '';
        };

        $scope._setAttended = function(ticket) {
            $scope.setTicketAttribute(ticket, 'attended', true, null, true);
        };

        $scope.deleteTicket = function(ticket) {
            EventTicket.delete({
                    event_id: $state.params.id,
                    ticket_id: ticket._id
                }, function() {
                    $scope._localRemoveTicket(ticket);
            });
        };

        $scope.addTicket = function(ticket) {
            ticket.event_id = $state.params.id;
            EventTicket.add(ticket, function(ret_ticket) {
                $log.debug('addTicket');
                $log.debug(ret_ticket);
                $scope._localAddTicket(ret_ticket, ticket);
                if (!$state.is('event.tickets')) {
                    $state.go('event.ticket.edit', {id: $scope.event._id, ticket_id: ret_ticket._id});
                } else {
                    $scope.query = '';
                    $scope._setAttended(ret_ticket);
                    if ($scope.$close) {
                        // Close the Quick ticket modal.
                        $scope.$close();
                    }
                }
            });
        };

        $scope.updateTicket = function(ticket, cb) {
            ticket.event_id = $state.params.id;
            EventTicket.update(ticket, function(t) {
                $scope._localUpdateTicket(t.ticket);
                if (cb) {
                    cb(t);
                }
            });
        };

        $scope.toggleCancelledTicket = function() {
            if (!$scope.ticket._id) {
                return;
            }
            $scope.ticket.cancelled = !$scope.ticket.cancelled;
            $scope.setTicketAttribute($scope.ticket, 'cancelled', $scope.ticket.cancelled, function() {
                $scope.guiOptions.dangerousActionsEnabled = false;
            });
        };

        $scope.openQuickAddTicket = function(_id) {
            var modalInstance = $uibModal.open({
                templateUrl: 'modal-quick-add-ticket.html',
                controller: 'EventTicketsCtrl'
            });
            modalInstance.result.then(function() {
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

        $scope.cancelForm = function() {
            if (!$state.is('event.tickets')) {
                $state.go('events');
            } else if ($scope.$close) {
                $scope.$close();
            }
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
            angular.forEach($scope.ticketsOrder,
                function(value, idx) {
                    if (value !== key && value !== inv_key) {
                        new_order.push(value);
                    }
                }
            );
            $scope.ticketsOrder = new_order;
        };

        $scope.showMessage = function(cfg) {
            $scope.message.show(cfg);
        };

        $scope.$on('$destroy', function() {
            $scope.EventUpdates && $scope.EventUpdates.close();
        });
    }]
);


eventManControllers.controller('UsersCtrl', ['$scope', '$rootScope', '$state', '$log', 'User', '$uibModal',
    function ($scope, $rootScope, $state, $log, User, $uibModal) {
        $scope.loginData = {};
        $scope.user = {};
        $scope.updateUserInfo = {};
        $scope.users = [];
        $scope.usersOrderProp = 'username';
        $scope.ticketsOrderProp = 'title';

        $scope.confirm_delete = 'Do you really want to delete this user?';
        $rootScope.$on('$translateChangeSuccess', function () {
            $translate('Do you really want to delete this user?').then(function (translation) {
                $scope.confirm_delete = translation;
            });
        });

        $scope.updateUsersList = function() {
            if ($state.is('users')) {
                $scope.users = User.all();
            }
        };

        $scope.updateUsersList();

        if ($state.is('user.edit') && $state.params.id) {
            $scope.user = User.get({id: $state.params.id}, function() {
                $scope.updateUserInfo = $scope.user;
            });
        }

        $scope.updateUser = function() {
            User.update($scope.updateUserInfo);
        };

        $scope.deleteUser = function(user_id) {
            var modalInstance = $uibModal.open({
                scope: $scope,
                templateUrl: 'modal-confirm-action.html',
                controller: 'ModalConfirmInstanceCtrl',
                resolve: {
                    message: function() { return $scope.confirm_delete; }
                }
            });
            modalInstance.result.then(function() {
                User.delete({id: user_id}, $scope.updateUsersList);
            });
        };

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
                    $rootScope.readInfo(function(info) {
                        $log.debug('logged in user: ' + info.user.username);
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
                        $log.debug('logged out user');
                        $state.go('login');
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

