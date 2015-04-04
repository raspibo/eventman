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

        $scope.updateAttendee = function(person, data) {
            $log.info('EventDetailsCtrl');
            $log.info('event_id: ' + $routeParams.id);
            $log.info('person_id: ' + person.person_id);
            $log.info('data:');
            $log.info(data);
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


eventManControllers.controller('PersonDetailsCtrl', ['$scope', '$routeParams', 'Person',
    function ($scope, $routeParams, Person) {
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
    }]
);


eventManControllers.controller('ImportPersonsCtrl', ['$scope', '$log',
    function ($scope, $log) {
            $scope.ebCSVimport = function() {
                $log.info("ImportPersonsCtrl");
                $log.info($scope);
        };
    }]
);


eventManControllers.controller('FileUploadCtrl', ['$scope', '$log', '$upload', 'Event',
    function ($scope, $log, $upload, Event) {
            $scope.file = null;
            $scope.reply = {};
            $scope.events = Event.all();
            $scope.upload = function(file, url) {
                $log.info("FileUploadCtrl.upload");
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

