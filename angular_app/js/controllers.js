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

