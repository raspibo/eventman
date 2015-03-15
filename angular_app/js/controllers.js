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


eventManControllers.controller('PersonsListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('/persons').success(function(data) {
            $scope.persons = data.persons;
        });
        $scope.orderProp = 'name';
    }]
);

