'use strict';

/* Controllers; their method are available where specified with the ng-controller
 * directive or for a given route (see app.js).  They use some services to
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
        $scope.orderProp = 'begin-datetime';

        $scope.remove = function(_id) {
            Event.remove({'id': _id}, function() {
                $scope.events = Event.all();
            });
        };
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', 'Event', '$routeParams', '$log',
    function ($scope, Event, $routeParams, $log) {
        if ($routeParams.id) {
            $scope.event = Event.get($routeParams);
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

        $scope.updateAttendee = function(person, attended) {
            $log.debug('EventDetailsCtrl.event_id: ' + $routeParams.id);
            $log.debug('EventDetailsCtrl.person_id: ' + person.person_id);
            $log.debug('EventDetailsCtrl.attended: ' + attended);
            Event.personAttended({
                    _id: $routeParams.id,
                    person_id: person.person_id,
                    'persons.$.attended': attended
                },
                function(data) {
                    $log.debug('EventDetailsCtrl.personAttended.data');
                    $log.debug(data);
                    $scope.event.persons = data;
            });
        };

        $scope.removeAttendee = function(person) {
            Event.deleteAttendee({
                    _id: $routeParams.id,
                    person_id: person.person_id
                },
                function(data) {
                    $scope.event.persons = data;
            });
        };
    }]
);


eventManControllers.controller('PersonsListCtrl', ['$scope', 'Person',
    function ($scope, Person) {
        $scope.persons = Person.all();
        $scope.orderProp = 'name';

        $scope.remove = function(_id) {
            Person.remove({'id': _id}, function() {
                $scope.persons = Person.all();
            });
        };
    }]
);


eventManControllers.controller('PersonDetailsCtrl', ['$scope', '$routeParams', 'Person', 'Event', '$log',
    function ($scope, $routeParams, Person, Event, $log) {
        if ($routeParams.id) {
            $scope.person = Person.get($routeParams);
            Person.getEvents($routeParams, function(data) {
                $scope.events = data;
            });
        }
        // store a new Person or update an existing one
        $scope.save = function() {
            if ($scope.person.id === undefined) {
                $scope.person = Person.save($scope.person);
            } else {
                $scope.person = Person.update($scope.person);
            }
        };
        $scope.updateAttendee = function(event, attended) {
            $log.debug('PersonDetailsCtrl.event_id: ' + $routeParams.id);
            $log.debug('PersonDetailsCtrl.event_id: ' + event.event_id);
            $log.debug('PersonDetailsCtrl.attended: ' + attended);
            Event.personAttended({
                    _id: event._id,
                    person_id: $routeParams.id,
                    'persons.$.attended': attended
                },
                function(data) {
                    Person.getEvents($routeParams, function(data) {
                        $log.debug('PersonDetailsCtrl.personAttended.data');
                        $log.debug(data);
                        $scope.events = data;
                    });
                }
            );
        }
    }]
);


eventManControllers.controller('ImportPersonsCtrl', ['$scope', '$log',
    function ($scope, $log) {
            $scope.ebCSVimport = function() {
                $log.debug("ImportPersonsCtrl");
                $log.debug($scope);
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

