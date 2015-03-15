'use strict';

/* Controllers */
var eventManControllers = angular.module('eventManControllers', []);


eventManControllers.controller('EventsListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('/events').success(function(data) {
            $scope.events = data.events;
        });
        $scope.orderProp = 'begin-datetime';
    }]
);


eventManControllers.controller('EventDetailsCtrl', ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {
        $http.get("/events/" + $routeParams.eventID).success(function(data) {

            $scope.event = data.event;
        });
    }]
);


eventManControllers.controller('PersonsListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('/persons').success(function(data) {
            $scope.persons = data.persons;
        });
        $scope.orderProp = 'name';
    }]
);


eventManControllers.controller('PersonDetailsCtrl', ['$scope', '$http', '$routeParams',
    function ($scope, $http, $routeParams) {
        $http.get("/persons/" + $routeParams.personID).success(function(data) {
            $scope.person = data.person;
        });
    }]
);

