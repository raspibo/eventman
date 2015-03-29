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


eventManControllers.controller('EventDetailsCtrl', ['$scope', 'Event', '$routeParams',
    function ($scope, Event, $routeParams) {
        if ($routeParams.id) {
            $scope.event = Event.get($routeParams);
        }
        // store a new Event or update an existing one
        $scope.save = function() {
                if ($scope.event.id === undefined) {
                    $scope.event = Event.save($scope.event);
                } else {
                    $scope.event = Event.update($scope.event);
                }
                $scope.eventForm.$dirty = false;
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


eventManControllers.controller('PersonDetailsCtrl', ['$scope', 'Person', '$routeParams',
    function ($scope, Person, $routeParams) {
        if ($routeParams.id) {
            $scope.person = Person.get($routeParams);
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


eventManControllers.controller('FileUploadCtrl', ['$scope', '$log', '$upload',
    function ($scope, $log, $upload) {
            $scope.file = null;
            $scope.reply = {};
            $scope.upload = function(file, url) {
                $log.info("FileUploadCtrl.upload");
                $upload.upload({
                    url: url,
                    file: file
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

