'use strict';

/* Controllers */
var eventManControllers = angular.module('eventManControllers', []);

eventManControllers.controller('navigation', ['$location',
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
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', 'Event', '$routeParams',
    function ($scope, Event, $routeParams) {
        if ($routeParams.id) {
            $scope.event = Event.get($routeParams);
        }
        $scope.save = function() {
                if ($scope.event.id === undefined) {
                    Event.save($scope.event);
                } else {
                    Event.update($scope.event);
                }
        };
    }]
);


eventManControllers.controller('PersonsListCtrl', ['$scope', 'Person',
    function ($scope, Person) {
        $scope.persons = Person.all();
        $scope.orderProp = 'name';
    }]
);


eventManControllers.controller('PersonDetailsCtrl', ['$scope', 'Person', '$routeParams',
    function ($scope, Person, $routeParams) {
        if ($routeParams.id) {
            $scope.person = Person.get($routeParams);
        }
        $scope.save = function() {
                if ($scope.person.id === undefined) {
                    Person.save($scope.person);
                } else {
                    Person.update($scope.person);
                }
        };
    }]
);

